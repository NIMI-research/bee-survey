import pandas as pd
from pathlib import Path
import re
from difflib import SequenceMatcher
from const import MAIN_CSV_PATH, SOURCE_WORKBOOK_PATH, VISUALIZATION_CSV_PATH


SOURCE_SHEET = "Sources"
REORGANIZE_SHEET = "Re-organize"

# Columns to keep from each sheet
REORGANIZE_COLUMNS = ["#", "year", "title", "authors", "subcategory (ai task)", "category (section)", "approach (ai)", "data modality"]
SOURCE_COLUMNS = ["papers", "url", "authors", "year", "abstract", "venue name", "data modality", "pass/fail", "search keyword", "approach (ai)", "research problem", "approach group"]

# Output column order (explicit) - category comes from Re-organize's "category (section)"
OUTPUT_COLUMNS = ["#", "title", "authors", "year", "subcategory (ai task)", "category (section)", "approach (ai)", "data modality", "url", "abstract", "venue name", "pass/fail", "search keyword", "research problem", "approach group"]

FUZZY_MATCH_THRESHOLD = 0.86
ALLOWED_SUBCATEGORY_PATTERNS = {
    "monitoring & health assessment",
    "classification",
    "detection",
    "tracking & pose estimation",
}


def _normalize_text(value):
    """Convert value to normalized string."""
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _title_match_key(value):
    """Normalize title for matching: lowercase, ignore bracketed text, remove symbols, collapse spaces."""
    text = _normalize_text(value).lower()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"\[[^\]]*\]", " ", text)
    text = re.sub(r"\{[^}]*\}", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _title_loose_match_key(value):
    """More tolerant title key: remove spaces after normalization (e.g., MobileNet == Mobile Net)."""
    return _title_match_key(value).replace(" ", "")


def _fuzzy_similarity(left_text, right_text):
    """Return fuzzy similarity ratio in [0, 1]."""
    if not left_text or not right_text:
        return 0.0
    return SequenceMatcher(None, left_text, right_text).ratio()


def _year_match_key(value):
    """Extract 4-digit year for matching; empty string if unavailable."""
    text = _normalize_text(value)
    if not text:
        return ""
    match = re.search(r"(?:19|20)\d{2}", text)
    return match.group(0) if match else ""


def _is_fail_value(value):
    """Check if pass/fail value indicates failure."""
    if not value:
        return False
    val = str(value).strip().lower()
    return val in ("fail", "failed", "f", "false")


def _capitalize_first_letter(column_name):
    """Capitalize only the first character of a column name."""
    text = _normalize_text(column_name)
    if not text:
        return text
    return text[0].upper() + text[1:]


def _subcategory_match_key(value):
    """Normalize subcategory value for matching allowed patterns."""
    text = _normalize_text(value).lower()
    text = text.replace("and", "&")
    text = re.sub(r"\s*&\s*", " & ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _filter_allowed_subcategories(df, column_name):
    """Keep only rows whose subcategory matches allowed patterns without bracket-tag prefixes."""
    if column_name not in df.columns:
        return df

    raw_values = df[column_name].map(_normalize_text)
    normalized = raw_values.map(_subcategory_match_key)
    has_bracket_prefix = raw_values.str.match(r"^\s*\[[^\]]+\]\s*", na=False)
    has_survey_text = raw_values.str.contains(r"\bsurvey\b", case=False, na=False)
    return df[
        normalized.isin(ALLOWED_SUBCATEGORY_PATTERNS)
        & ~has_bracket_prefix
        & ~has_survey_text
    ].copy()


def _normalize_column_name(name):
    """Convert column name to lowercase alphanumeric."""
    if name is None:
        return ""
    return "".join(c.lower() for c in str(name).strip() if c.isalnum())


def _find_column(columns, candidates):
    """Find first matching column from candidates list."""
    normalized = {_normalize_column_name(col): col for col in columns}
    for candidate in candidates:
        candidate_key = _normalize_column_name(candidate)
        if candidate_key in normalized:
            return normalized[candidate_key]
    return None


def _get_subset_columns(df, desired_columns):
    """Extract only desired columns from dataframe, using flexible matching."""
    subset = pd.DataFrame()
    for desired in desired_columns:
        col = _find_column(df.columns, [desired])
        if col:
            subset[desired.lower()] = df[col].map(_normalize_text)
    return subset


def _merge_sheets_on_title(source_df, reorganize_df):
    """
    Merge source and reorganize sheets on title.
    Reorganize has # (serial) which defines order.
    For duplicate columns, prefer reorganize values.
    Keeps Re-organize columns as-is (including "category (section)").
    """
    # Find title columns
    source_title_col = _find_column(source_df.columns, ["papers", "title"])
    reorg_title_col = _find_column(reorganize_df.columns, ["title"])
    
    if not source_title_col or not reorg_title_col:
        raise ValueError("Could not find title column in one or both sheets")
    
    source_prepared = source_df.copy().fillna("")
    reorg_prepared = reorganize_df.copy().fillna("")

    source_prepared["__title_loose_key"] = source_prepared[source_title_col].map(_title_loose_match_key)
    reorg_prepared["__title_loose_key"] = reorg_prepared[reorg_title_col].map(_title_loose_match_key)

    source_year_col = _find_column(source_prepared.columns, ["year"])
    reorg_year_col = _find_column(reorg_prepared.columns, ["year"])

    if source_year_col:
        source_prepared["__year_key"] = source_prepared[source_year_col].map(_year_match_key)
    else:
        source_prepared["__year_key"] = ""

    if reorg_year_col:
        reorg_prepared["__year_key"] = reorg_prepared[reorg_year_col].map(_year_match_key)
    else:
        reorg_prepared["__year_key"] = ""

    # Exact matching index for reorganize rows
    reorg_exact_index = {}
    for reorg_idx, row in reorg_prepared.iterrows():
        exact_key = (row["__title_loose_key"], row["__year_key"])
        reorg_exact_index.setdefault(exact_key, []).append(reorg_idx)

    used_reorg_indices = set()
    matched_pairs = []
    unmatched_source_indices = []

    # 1) Exact match first
    for src_idx, src_row in source_prepared.iterrows():
        exact_key = (src_row["__title_loose_key"], src_row["__year_key"])
        candidates = reorg_exact_index.get(exact_key, [])
        picked = None
        for candidate_idx in candidates:
            if candidate_idx not in used_reorg_indices:
                picked = candidate_idx
                break

        if picked is not None:
            used_reorg_indices.add(picked)
            matched_pairs.append((src_idx, picked))
        else:
            unmatched_source_indices.append(src_idx)

    # 2) Fuzzy match remaining source rows to remaining reorganize rows
    remaining_reorg_indices = [idx for idx in reorg_prepared.index if idx not in used_reorg_indices]

    for src_idx in unmatched_source_indices:
        src_row = source_prepared.loc[src_idx]
        src_title_key = src_row["__title_loose_key"]
        src_year_key = src_row["__year_key"]

        best_reorg_idx = None
        best_score = 0.0

        for reorg_idx in remaining_reorg_indices:
            if reorg_idx in used_reorg_indices:
                continue

            reorg_row = reorg_prepared.loc[reorg_idx]
            reorg_title_key = reorg_row["__title_loose_key"]
            reorg_year_key = reorg_row["__year_key"]

            # If both years are present and different, skip candidate.
            if src_year_key and reorg_year_key and src_year_key != reorg_year_key:
                continue

            score = _fuzzy_similarity(src_title_key, reorg_title_key)
            if score > best_score:
                best_score = score
                best_reorg_idx = reorg_idx

        if best_reorg_idx is not None and best_score >= FUZZY_MATCH_THRESHOLD:
            used_reorg_indices.add(best_reorg_idx)
            matched_pairs.append((src_idx, best_reorg_idx))

    # Consolidate rows: prefer reorganize values where available.
    helper_cols = {"__title_loose_key", "__year_key"}
    source_cols = [col for col in source_prepared.columns if col not in helper_cols]
    reorg_cols = [col for col in reorg_prepared.columns if col not in helper_cols]
    all_cols = list(dict.fromkeys(source_cols + reorg_cols))

    consolidated_rows = []

    matched_source_set = {src_idx for src_idx, _ in matched_pairs}
    matched_reorg_set = {reorg_idx for _, reorg_idx in matched_pairs}

    for src_idx, reorg_idx in matched_pairs:
        src_row = source_prepared.loc[src_idx]
        reorg_row = reorg_prepared.loc[reorg_idx]
        merged_row = {}
        for col in all_cols:
            src_val = _normalize_text(src_row.get(col, ""))
            reorg_val = _normalize_text(reorg_row.get(col, ""))
            merged_row[col] = reorg_val if reorg_val else src_val
        consolidated_rows.append(merged_row)

    for src_idx, src_row in source_prepared.iterrows():
        if src_idx in matched_source_set:
            continue
        merged_row = {col: _normalize_text(src_row.get(col, "")) for col in all_cols}
        consolidated_rows.append(merged_row)

    for reorg_idx, reorg_row in reorg_prepared.iterrows():
        if reorg_idx in matched_reorg_set:
            continue
        merged_row = {col: _normalize_text(reorg_row.get(col, "")) for col in all_cols}
        consolidated_rows.append(merged_row)

    return pd.DataFrame(consolidated_rows)


def build_visualization_csv_from_workbook(
    input_path=SOURCE_WORKBOOK_PATH,
    output_path=VISUALIZATION_CSV_PATH,
):
    """Build Visualization.csv by merging Sources and Re-organize sheets."""
    input_path = Path(input_path)
    output_path = Path(output_path)

    # Validate input file exists
    if not input_path.exists():
        raise FileNotFoundError(f"Input workbook not found: {input_path}")

    # Check that required sheets exist
    xl_file = pd.ExcelFile(input_path)
    missing_sheets = [sheet for sheet in [SOURCE_SHEET, REORGANIZE_SHEET] if sheet not in xl_file.sheet_names]
    if missing_sheets:
        raise ValueError(f"Missing required sheets in workbook: {missing_sheets}")

    # Read sheets (raw, no column filtering for now)
    source_raw = pd.read_excel(input_path, sheet_name=SOURCE_SHEET, dtype=str)
    reorganize_raw = pd.read_excel(input_path, sheet_name=REORGANIZE_SHEET, dtype=str)

    # Extract only desired columns and normalize
    source = _get_subset_columns(source_raw, SOURCE_COLUMNS)
    reorganize = _get_subset_columns(reorganize_raw, REORGANIZE_COLUMNS)

    # Merge on title
    merged = _merge_sheets_on_title(source, reorganize)

    # Filter: require title and authors
    if "title" not in merged.columns:
        raise ValueError("Title column not found in merged data")
    if "authors" not in merged.columns:
        raise ValueError("Authors column not found in merged data")

    merged = merged[merged["title"].map(bool) & merged["authors"].map(bool)].copy()

    # Filter: exclude rows with fail/failed/f/false in pass/fail column
    if "pass/fail" in merged.columns:
        merged = merged[~merged["pass/fail"].map(_is_fail_value)].copy()

    # Filter: keep only supported subcategory patterns
    merged = _filter_allowed_subcategories(merged, "subcategory (ai task)")

    # Remove duplicate titles (keep first occurrence by #)
    if "#" in merged.columns:
        merged = merged.sort_values(by=["#"], na_position="last", key=lambda x: pd.to_numeric(x, errors="coerce")).reset_index(drop=True)
    merged = merged.drop_duplicates(subset=["title"], keep="first")

    # Reorder columns according to OUTPUT_COLUMNS (only keep those that exist)
    existing_cols = [col for col in OUTPUT_COLUMNS if col in merged.columns]
    merged = merged[existing_cols]

    # Capitalize first letter of output headers
    merged = merged.rename(columns={col: _capitalize_first_letter(col) for col in merged.columns})

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


def build_visualization_csv_from_main_csv(
    main_csv_path=MAIN_CSV_PATH,
    output_path=VISUALIZATION_CSV_PATH,
):
    """Fallback: build Visualization.csv from existing main CSV."""
    main_csv_path = Path(main_csv_path)
    output_path = Path(output_path)

    # Validate input file exists
    if not main_csv_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {main_csv_path}")

    # Read and extract desired columns
    df_raw = pd.read_csv(main_csv_path, dtype=str).fillna("")
    df = _get_subset_columns(df_raw, SOURCE_COLUMNS)

    # Filter: require title and authors
    if "title" not in df.columns:
        raise ValueError("Title column not found in CSV")
    if "authors" not in df.columns:
        raise ValueError("Authors column not found in CSV")

    df = df[df["title"].map(bool) & df["authors"].map(bool)].copy()

    # Filter: exclude rows with fail/failed/f/false in pass/fail column
    if "pass/fail" in df.columns:
        df = df[~df["pass/fail"].map(_is_fail_value)].copy()

    # Filter: keep only supported subcategory patterns (if available in fallback CSV)
    df = _filter_allowed_subcategories(df, "subcategory (ai task)")

    # Remove duplicate titles
    df = df.drop_duplicates(subset=["title"], keep="first")

    # Sort by title (fallback has no # ordering)
    df = df.sort_values(by=["title"], key=lambda x: x.str.lower()).reset_index(drop=True)

    # Reorder columns according to OUTPUT_COLUMNS (only keep those that exist)
    existing_cols = [col for col in OUTPUT_COLUMNS if col in df.columns]
    df = df[existing_cols]

    # Capitalize first letter of output headers
    df = df.rename(columns={col: _capitalize_first_letter(col) for col in df.columns})

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


class LiteratureDataset:

    def __init__(self, csv_path=VISUALIZATION_CSV_PATH):
        self.csv_path = Path(csv_path)
        self.df = None

    def ensure_dataset(self):
        """Build and overwrite visualization CSV."""
        if Path(SOURCE_WORKBOOK_PATH).exists():
            build_visualization_csv_from_workbook(
                input_path=SOURCE_WORKBOOK_PATH,
                output_path=self.csv_path,
            )
        elif Path(MAIN_CSV_PATH).exists():
            build_visualization_csv_from_main_csv(
                main_csv_path=MAIN_CSV_PATH,
                output_path=self.csv_path,
            )
        else:
            raise FileNotFoundError(
                f"Could not build dataset. Missing both workbook '{SOURCE_WORKBOOK_PATH}' and CSV '{MAIN_CSV_PATH}'."
            )

    def load(self):
        """Load CSV as pandas DataFrame."""
        self.ensure_dataset()
        self.df = pd.read_csv(self.csv_path)
        subcategory_col = _find_column(self.df.columns, ["subcategory (ai task)"])
        if subcategory_col:
            self.df = _filter_allowed_subcategories(self.df, subcategory_col)
        return self.df

    def get(self):
        """Return dataframe without reloading."""
        if self.df is None:
            return self.load()
        return self.df