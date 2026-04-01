import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

from const import INPUT_DIR, MAIN_CSV_PATH, SOURCE_WORKBOOK_PATH, VISUALIZATION_CSV_PATH


SOURCE_SHEET = "Sources"
REORGANIZE_SHEET = "Re-organize"
FUZZY_MATCH_THRESHOLD = 0.86

OUTPUT_COLUMNS = [
    "#",
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
    "#": ["#", "serial", "no"],
    "title": ["title", "papers", "paper"],
    "authors": ["authors", "author"],
    "year": ["year", "publication year"],
    "subcategory (ai task)": ["subcategory (ai task)", "subcategory", "ai task"],
    "category (section)": ["category (section)", "category section", "category"],
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
    "monitoring & health assessment",
    "classification",
    "detection",
    "tracking & pose estimation",
}

ISO_CODES_PATH = INPUT_DIR / "iso_codes.csv"

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


def _canonicalize(df):
    out = pd.DataFrame()
    for canonical, candidates in COLUMN_CANDIDATES.items():
        found = _find_column(df.columns, [canonical, *candidates])
        if found:
            out[canonical] = df[found].map(_normalize_text)
    for col in OUTPUT_COLUMNS:
        if col not in out.columns:
            out[col] = ""
    return out[OUTPUT_COLUMNS]


def _title_key(value):
    text = _normalize_text(value).lower()
    text = re.sub(r"\([^)]*\)|\[[^\]]*\]|\{[^}]*\}", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", "", text)


def _year_key(value):
    match = re.search(r"(?:19|20)\d{2}", _normalize_text(value))
    return match.group(0) if match else ""


def _fuzzy_similarity(left_text, right_text):
    if not left_text or not right_text:
        return 0.0
    return SequenceMatcher(None, left_text, right_text).ratio()


def _coalesce_rows(primary, secondary):
    return {
        col: _normalize_text(primary.get(col, "")) or _normalize_text(secondary.get(col, ""))
        for col in OUTPUT_COLUMNS
    }


def _merge_primary_reorganize(primary_df, reorg_df):
    primary = primary_df.copy()
    reorg = reorg_df.copy()

    primary["__title_key"] = primary["title"].map(_title_key)
    reorg["__title_key"] = reorg["title"].map(_title_key)
    primary["__year_key"] = primary["year"].map(_year_key)
    reorg["__year_key"] = reorg["year"].map(_year_key)

    used_reorg = set()
    pairs = []
    unmatched_primary = []

    exact_map = {}
    for ridx, row in reorg.iterrows():
        exact_map.setdefault((row["__title_key"], row["__year_key"]), []).append(ridx)

    for sidx, row in primary.iterrows():
        candidates = exact_map.get((row["__title_key"], row["__year_key"]), [])
        pick = next((ridx for ridx in candidates if ridx not in used_reorg), None)
        if pick is None:
            unmatched_primary.append(sidx)
        else:
            used_reorg.add(pick)
            pairs.append((sidx, pick))

    for sidx in unmatched_primary:
        src = primary.loc[sidx]
        best_idx, best_score = None, 0.0
        for ridx, reg in reorg.iterrows():
            if ridx in used_reorg:
                continue
            if src["__year_key"] and reg["__year_key"] and src["__year_key"] != reg["__year_key"]:
                continue
            score = _fuzzy_similarity(src["__title_key"], reg["__title_key"])
            if score > best_score:
                best_idx, best_score = ridx, score
        if best_idx is not None and best_score >= FUZZY_MATCH_THRESHOLD:
            used_reorg.add(best_idx)
            pairs.append((sidx, best_idx))

    rows = []
    matched_primary = {sidx for sidx, _ in pairs}

    for sidx, ridx in pairs:
        src_row = primary.loc[sidx].to_dict()
        reg_row = reorg.loc[ridx].to_dict()
        rows.append(_coalesce_rows(reg_row, src_row))

    for sidx, src in primary.iterrows():
        if sidx not in matched_primary:
            rows.append(_coalesce_rows(src.to_dict(), {}))

    for ridx, reg in reorg.iterrows():
        if ridx not in used_reorg:
            rows.append(_coalesce_rows(reg.to_dict(), {}))

    return pd.DataFrame(rows)


def _is_fail_value(value):
    return _normalize_text(value).lower() in {"false", "f", "fail", "failed"}


def _subcategory_match_key(value):
    text = _normalize_text(value).lower().replace("and", "&")
    text = re.sub(r"\s*&\s*", " & ", text)
    return re.sub(r"\s+", " ", text).strip()


def _apply_reorganize_rules(df):
    if "subcategory (ai task)" not in df.columns:
        return df
    raw = df["subcategory (ai task)"].map(_normalize_text)
    normalized = raw.map(_subcategory_match_key)
    return df[
        normalized.isin(ALLOWED_SUBCATEGORY_PATTERNS)
        & ~raw.str.match(r"^\s*\[[^\]]+\]\s*", na=False)
        & ~raw.str.contains(r"\bsurvey\b", case=False, na=False)
        & ~raw.str.contains(r"\bout\s*of\s*scope\b", case=False, na=False)
    ].copy()


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

    if ISO_CODES_PATH.exists():
        iso_df = pd.read_csv(ISO_CODES_PATH, dtype=str).fillna("")
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


def _add_country_iso_columns(df):
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


def _finalize(df, sort_by_number):
    required = {"title", "authors"}
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    out = df.copy()
    out = out[out["title"].map(bool) & out["authors"].map(bool)]
    out = out[~out["pass/fail"].map(_is_fail_value)]
    out = _apply_reorganize_rules(out)
    out = out.drop_duplicates(subset=["title"], keep="first")
    out = _add_country_iso_columns(out)

    if sort_by_number:
        out = out.sort_values(by="#", key=lambda s: pd.to_numeric(s, errors="coerce"), na_position="last")
    else:
        out = out.sort_values(by="title", key=lambda s: s.str.lower())

    out = out.reset_index(drop=True)
    out = out[OUTPUT_COLUMNS]
    return out.rename(columns={col: col[:1].upper() + col[1:] for col in out.columns})


def _write_visualization_csv(df, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


def build_visualization_csv_from_workbook(input_path=SOURCE_WORKBOOK_PATH, output_path=VISUALIZATION_CSV_PATH):
    input_path = Path(input_path)
    output_path = Path(output_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input workbook not found: {input_path}")

    xl = pd.ExcelFile(input_path)
    missing = [sheet for sheet in (SOURCE_SHEET, REORGANIZE_SHEET) if sheet not in xl.sheet_names]
    if missing:
        raise ValueError(f"Missing required sheets in workbook: {missing}")

    if Path(MAIN_CSV_PATH).exists():
        primary = _canonicalize(pd.read_csv(MAIN_CSV_PATH, dtype=str).fillna(""))
    else:
        primary = _canonicalize(pd.read_excel(input_path, sheet_name=SOURCE_SHEET, dtype=str).fillna(""))

    reorg = _canonicalize(pd.read_excel(input_path, sheet_name=REORGANIZE_SHEET, dtype=str).fillna(""))
    merged = _merge_primary_reorganize(primary, reorg)
    final = _finalize(merged, sort_by_number=True)
    return _write_visualization_csv(final, output_path)


def build_visualization_csv_from_main_csv(main_csv_path=MAIN_CSV_PATH, output_path=VISUALIZATION_CSV_PATH):
    main_csv_path = Path(main_csv_path)
    output_path = Path(output_path)
    if not main_csv_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {main_csv_path}")

    main_df = _canonicalize(pd.read_csv(main_csv_path, dtype=str).fillna(""))
    final = _finalize(main_df, sort_by_number=False)
    return _write_visualization_csv(final, output_path)


class LiteratureDataset:
    def __init__(self, csv_path=VISUALIZATION_CSV_PATH):
        self.csv_path = Path(csv_path)
        self.df = None

    def ensure_dataset(self):
        if Path(SOURCE_WORKBOOK_PATH).exists():
            build_visualization_csv_from_workbook(input_path=SOURCE_WORKBOOK_PATH, output_path=self.csv_path)
        elif Path(MAIN_CSV_PATH).exists():
            build_visualization_csv_from_main_csv(main_csv_path=MAIN_CSV_PATH, output_path=self.csv_path)
        else:
            raise FileNotFoundError(
                f"Could not build dataset. Missing both workbook '{SOURCE_WORKBOOK_PATH}' and CSV '{MAIN_CSV_PATH}'."
            )

    def load(self):
        self.ensure_dataset()
        self.df = pd.read_csv(self.csv_path)
        return self.df

    def get(self):
        return self.load() if self.df is None else self.df