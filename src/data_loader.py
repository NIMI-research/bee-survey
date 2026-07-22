"""
Data Loader for Bee-AI Literature Survey

This module loads, canonicalizes, normalizes, and deduplicates literature data from the main CSV
for the Bee-AI research survey. It handles:

- Column name mapping and standardization
- Text normalization and fuzzy matching for duplicate detection
- ISO code resolution and country/region standardization
- Data validation and subcategory filtering
- Deduplication of records within the main CSV

The module provides functions to load data from MAIN_CSV_PATH, canonicalizing all data to a
consistent output schema with standardized columns.
"""

import re
import unicodedata
import logging
from pathlib import Path

import pandas as pd

from const import MAIN_CSV_PATH, SOURCE_WORKBOOK_PATH, VISUALIZATION_CSV_PATH

logger = logging.getLogger(__name__)

OUTPUT_COLUMNS = [
    "title",
    "authors",
    "year",
    "subcategory (ai task)",
    "category (section)",
    "approach (ai)",
    "data modality",
    "url",
    "abstract",
    "venue name",
    "pass/fail",
    "search keyword",
    "research problem",
    "bee demographic",
    "research demographic",
    "bee_country",
    "bee_iso",
    "research_country",
    "research_iso",
    "Country",
    "Iso_code",
    "collection time",
    "approach group",
]

COLUMN_CANDIDATES = {
    "title": ["title", "papers", "paper"],
    "authors": ["authors", "author"],
    "year": ["year", "publication year"],
    "subcategory (ai task)": ["subcategory (ai task)", "subcategory", "ai task", "category"],
    "category (section)": ["category (section)", "category section"],
    "approach (ai)": ["approach (ai)", "approach", "ai approach", "method", "methodology"],
    "data modality": ["data modality", "data modality/format", "modality", "data type"],
    "url": ["url", "link", "paper url", "source url"],
    "abstract": ["abstract", "summary"],
    "venue name": ["venue name", "venue"],
    "pass/fail": ["pass/fail", "pass fail", "pass_fail"],
    "search keyword": ["search keyword", "search keywords", "keyword", "keywords"],
    "research problem": ["research problem", "problem", "research task"],
    "bee demographic": ["bee demographic", "bee demographics", "bee demography"],
    "research demographic": ["research demographic", "research demographics", "study demographic", "study demographics"],
    "Country": ["country"],
    "Iso_code": ["iso_code", "iso code", "alpha-3", "alpha3", "iso3"],
    "collection time": ["collection time", "time of collection", "sampling time"],
    "approach group": ["approach group", "approachgroup"],
}

ALLOWED_SUBCATEGORY_PATTERNS = {
    "monitoring & predictive health analytics",
    "classification",
    "detection",
    "tracking & pose estimation",
}

ISO_CODES_SHEET = "iso_codes"

ISO_ALIAS_TO_CODE = {
    "US": "USA",
    "USA": "USA",
    "United States": "USA",
    "California": "USA",
    "United States of America": "USA",
    "America": "USA",
    "UK": "GBR",
    "U.K.": "GBR",
    "United Kingdom": "GBR",
    "Great Britain": "GBR",
    "Turkey": "TUR",
    "Türkiye": "TUR",
}

ISO_DISPLAY_OVERRIDES = {
    "USA": "United States",
    "GBR": "United Kingdom",
}

_ISO_LOOKUP_CACHE = None
_ISO_CODE_TO_COUNTRY_CACHE = None


def _normalize_text(value):
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _normalize_column_name(name):
    if name is None:
        return ""
    return "".join(c.lower() for c in str(name).strip() if c.isalnum())


def _find_column(columns, candidates):
    normalized = {_normalize_column_name(col): col for col in columns}
    for candidate in candidates:
        found = normalized.get(_normalize_column_name(candidate))
        if found:
            return found
    return None


def load_csv(csv_path):
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {csv_path}")
    return pd.read_csv(csv_path, dtype=str).fillna("")

def canonicalize_columns(df):
    out = pd.DataFrame()
    for canonical, candidates in COLUMN_CANDIDATES.items():
        found = _find_column(df.columns, [canonical, *candidates])
        if found:
            out[canonical] = df[found].map(_normalize_text)
    for col in OUTPUT_COLUMNS:
        if col not in out.columns:
            out[col] = ""
    return out[OUTPUT_COLUMNS]


def _standardize_title(value):
    title = _normalize_text(value)
    if not title:
        return ""
    compact = re.sub(r"\s+", " ", title).strip()
    return compact


def _paper_label(row):
    title = _normalize_text(row.get("title"))
    if title:
        return title
    authors = _normalize_text(row.get("authors"))
    if authors:
        return f"<untitled; authors={authors}>"
    return "<untitled>"


def _log_discarded_rows(stage, discarded_rows, reason):
    for _, row in discarded_rows.iterrows():
        logger.debug("Discarding paper at %s: %s | %s", stage, _paper_label(row), reason)


def _is_fail_value(value):
    return _normalize_text(value).lower() in {"false", "f", "fail", "failed"}


def _subcategory_match_key(value):
    text = _normalize_text(value).lower().replace("and", "&")
    text = re.sub(r"\s*&\s*", " & ", text)
    return re.sub(r"\s+", " ", text).strip()


def filter_pass_fail(df):
    if "pass/fail" not in df.columns:
        return df.copy()
    fail_mask = df["pass/fail"].map(_is_fail_value) | df["pass/fail"].isna()
    _log_discarded_rows("pass/fail", df[fail_mask], "pass/fail is marked as fail")
    return df[~fail_mask].copy()


def filter_subcategories(df):
    if "subcategory (ai task)" not in df.columns:
        return df.copy()
    raw = df["subcategory (ai task)"].map(_normalize_text)
    normalized = raw.map(_subcategory_match_key)
    allowed_mask = normalized.isin(ALLOWED_SUBCATEGORY_PATTERNS)
    bracket_mask = raw.str.match(r"^\s*\[[^\]]+\]\s*", na=False)
    survey_mask = raw.str.contains(r"\bsurvey\b", case=False, na=False)
    out_of_scope_mask = raw.str.contains(r"\bout\s*of\s*scope\b", case=False, na=False)
    keep_mask = allowed_mask & ~bracket_mask & ~survey_mask & ~out_of_scope_mask

    for idx in df.index[~keep_mask]:
        reasons = []
        if not allowed_mask.loc[idx]:
            reasons.append("subcategory is not in the allowed scope")
        if bracket_mask.loc[idx]:
            reasons.append("subcategory is bracket-tagged")
        if survey_mask.loc[idx]:
            reasons.append("subcategory mentions survey")
        if out_of_scope_mask.loc[idx]:
            reasons.append("subcategory is marked out of scope")
        _log_discarded_rows(
            "subcategory",
            df.loc[[idx]],
            "; ".join(reasons) if reasons else "subcategory did not pass the filter",
        )

    return df[keep_mask].copy()


def _normalize_geo_key(value):
    text = _normalize_text(value)
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _clean_demographic_text(value):
    text = _normalize_text(value)
    if not text or text == "-":
        return ""
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text or text == "-":
        return ""
    return text


def _load_iso_lookup():
    global _ISO_LOOKUP_CACHE, _ISO_CODE_TO_COUNTRY_CACHE
    if _ISO_LOOKUP_CACHE is not None and _ISO_CODE_TO_COUNTRY_CACHE is not None:
        return _ISO_LOOKUP_CACHE, _ISO_CODE_TO_COUNTRY_CACHE

    lookup = {}
    code_to_country = {}

    if Path(SOURCE_WORKBOOK_PATH).exists():
        try:
            iso_df = pd.read_excel(
                SOURCE_WORKBOOK_PATH,
                sheet_name=ISO_CODES_SHEET,
                dtype=str,
            ).fillna("")
        except Exception:
            iso_df = pd.DataFrame()

        for _, row in iso_df.iterrows():
            name = _normalize_text(row.get("name"))
            alpha2 = _normalize_text(row.get("alpha-2")).upper()
            alpha3 = _normalize_text(row.get("alpha-3")).upper()
            if not name or not alpha3:
                continue

            # Soft aliases from official ISO names, e.g.:
            # "Taiwan, Province of China" -> "Taiwan"
            name_before_comma = _normalize_text(name.split(",", 1)[0])
            name_before_paren = _normalize_text(name.split("(", 1)[0])

            code_to_country[alpha3] = name
            for key in {
                _normalize_geo_key(name),
                _normalize_geo_key(name_before_comma),
                _normalize_geo_key(name_before_paren),
                _normalize_geo_key(alpha2),
                _normalize_geo_key(alpha3),
            }:
                if key:
                    lookup[key] = alpha3

    for alias, code in ISO_ALIAS_TO_CODE.items():
        lookup[_normalize_geo_key(alias)] = code

    for code, country in ISO_DISPLAY_OVERRIDES.items():
        code_to_country[code] = country

    _ISO_LOOKUP_CACHE = lookup
    _ISO_CODE_TO_COUNTRY_CACHE = code_to_country
    return _ISO_LOOKUP_CACHE, _ISO_CODE_TO_COUNTRY_CACHE


def _resolve_country_iso_from_text(value, lookup, code_to_country):
    cleaned = _clean_demographic_text(value)
    if not cleaned:
        return "", ""

    before_comma = cleaned.split(",", 1)[0].strip()
    first_word = before_comma.split()[0] if before_comma else ""

    candidate_keys = []
    for candidate in (cleaned, before_comma, first_word):
        key = _normalize_geo_key(candidate)
        if key and key not in candidate_keys:
            candidate_keys.append(key)

    for key in candidate_keys:
        alpha3 = lookup.get(key)
        if alpha3:
            return code_to_country.get(alpha3, ""), alpha3

    # Soft mapping: if any word token matches an ISO code/alias key, map it.
    # Example: "collected in USA region" -> USA.
    word_tokens = re.findall(r"[A-Za-z0-9]+", cleaned)
    for token in word_tokens:
        token_key = _normalize_geo_key(token)
        if not token_key:
            continue
        alpha3 = lookup.get(token_key)
        if alpha3:
            return code_to_country.get(alpha3, ""), alpha3

    return "", ""


def _derive_specific_country_iso(row, source_col, lookup, code_to_country):
    return _resolve_country_iso_from_text(row.get(source_col, ""), lookup, code_to_country)


def add_country_iso(df):
    lookup, code_to_country = _load_iso_lookup()
    out = df.copy()

    bee_resolved = out.apply(
        lambda row: _derive_specific_country_iso(row, "bee demographic", lookup, code_to_country),
        axis=1,
    )
    out["bee_country"] = bee_resolved.map(lambda item: item[0])
    out["bee_iso"] = bee_resolved.map(lambda item: item[1])

    research_resolved = out.apply(
        lambda row: _derive_specific_country_iso(row, "research demographic", lookup, code_to_country),
        axis=1,
    )
    out["research_country"] = research_resolved.map(lambda item: item[0])
    out["research_iso"] = research_resolved.map(lambda item: item[1])

    out["Country"] = out["bee_country"].where(out["bee_iso"].map(bool), out["research_country"])
    out["Iso_code"] = out["bee_iso"].where(out["bee_iso"].map(bool), out["research_iso"])
    return out

def _standardize_title(value):
    title = _normalize_text(value)
    if not title:
        return ""
    compact = re.sub(r"\s+", " ", title).strip()
    return compact


def remove_duplicates(df):
    if "title" not in df.columns:
        return df.copy()

    out = df.copy()
    out["title"] = out["title"].map(_standardize_title)

    merged_rows = []
    used = set()

    for i, row_a in out.iterrows():
        if i in used:
            continue
        merged = row_a.copy()
        used.add(i)
        for j, row_b in out.iterrows():
            if j <= i or j in used:
                continue
            title_a = str(row_a["title"]).lower()
            title_b = str(row_b["title"]).lower()
            if title_a and title_b and (title_a in title_b or title_b in title_a):
                logger.debug(
                    "Discarding paper during duplicate merge: %s | merged into %s because titles overlap",
                    _paper_label(row_b),
                    _paper_label(row_a),
                )
                # Keep title A as ground truth
                for col in out.columns:
                    if pd.isna(merged[col]) or merged[col] == "":
                        merged[col] = row_b[col]
                used.add(j)
        merged_rows.append(merged)

    return pd.DataFrame(merged_rows).reset_index(drop=True)

def sort(df, sort_by_number=False):
    out = df.copy()
    return out.sort_values(by="title", key=lambda s: s.str.lower())


def _finalize(df, sort_by_number):
    required = {"title", "authors"}
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    out = df.copy()
    counts = {"start": len(out)}

    out = filter_pass_fail(out)
    counts["after_pass_fail"] = len(out)

    out = filter_subcategories(out)
    counts["after_subcategory"] = len(out)

    missing_title_or_authors = out[~(out["title"].map(bool) & out["authors"].map(bool))]
    _log_discarded_rows("required fields", missing_title_or_authors, "missing title or authors")
    out = out[out["title"].map(bool) & out["authors"].map(bool)]
    counts["after_title_authors"] = len(out)

    out = remove_duplicates(out)
    counts["after_dedup"] = len(out)

    out = add_country_iso(out)
    out = sort(out, sort_by_number=sort_by_number)

    out = out.reset_index(drop=True)
    out = out[OUTPUT_COLUMNS]

    logger.info("Row counts by stage: %s", counts)
    print("Row counts by stage:")
    prev = counts["start"]
    for stage, n in counts.items():
        print(f"  {stage}: {n} (dropped {prev - n})")
        prev = n

    return out.rename(columns={col: col[:1].upper() + col[1:] for col in out.columns})

def _write_visualization_csv(df, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


def build_visualization_csv_from_main_csv(main_csv_path=MAIN_CSV_PATH, output_path=VISUALIZATION_CSV_PATH):
    main_df = canonicalize_columns(load_csv(main_csv_path))
    final = _finalize(main_df, sort_by_number=False)
    return _write_visualization_csv(final, Path(output_path))


class LiteratureDataset:
    def __init__(self, main_csv_path=MAIN_CSV_PATH, csv_path=VISUALIZATION_CSV_PATH):
        self.main_csv_path = Path(main_csv_path)
        self.csv_path = Path(csv_path)
        self.df = None

    def ensure_dataset(self):
        build_visualization_csv_from_main_csv(main_csv_path=self.main_csv_path, output_path=self.csv_path)

    def load(self):
        self.ensure_dataset()
        self.df = pd.read_csv(self.csv_path)
        return self.df

    def get(self):
        return self.load() if self.df is None else self.df