import csv
from importlib.resources import path
import math
from os import path
import os
import re

# Example guide: could be loaded from Excel/CSV


import openpyxl

from const import MAIN_CSV_PATH, SOURCE_WORKBOOK_PATH


SOURCE_SHEETS = [
    "New-original 2024-2025",
    "Pass",
    "Original",
    "original-2011-2023",
]
GUIDE_SHEET = "Guides/Notes"

OUTPUT_COLUMNS = [
    "Papers",
    "URL",
    "Authors",
    "Year",
    "Abstract",
    "Venue Name",
    "Data modality",
    "Pass/Fail",
    "Search Keyword",
    "Approach (AI)",
    "Research Problem",
    "Category",
]

def _normalize_header(name):
    if name is None:
        return ""
    return re.sub(r"[^a-z0-9]", "", str(name).strip().lower())


def _to_int_year(value, default=-1):
    if value is None:
        return default

    if isinstance(value, bool):
        return default

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        if math.isnan(value):
            return default
        return int(value)

    text = str(value).strip()
    if not text:
        return default

    try:
        number = float(text)
        if not math.isnan(number):
            return int(number)
    except (TypeError, ValueError):
        pass

    year_matches = re.findall(r"(?:19|20)\d{2}", text)
    if year_matches:
        return max(int(y) for y in year_matches)

    any_int = re.search(r"-?\d+", text)
    if any_int:
        try:
            return int(any_int.group(0))
        except ValueError:
            return default

    return default


def _coerce_year_for_output(value):
    parsed = _to_int_year(value, default=None)
    return "" if parsed is None else parsed


def _text(value):
    return "" if value is None else str(value).strip()

def _extract_venue_name(raw_value, paper_text=""):
    venue_text = _text(raw_value)
    if venue_text:
        cleaned = re.sub(r"\s+", " ", venue_text)
        return cleaned

    text = _text(paper_text)
    if not text:
        return ""

    patterns = [
        r"\b(?:in|at)\s+([A-Z][A-Za-z0-9,&\-\s]{3,}?)(?:\.|,|;|$)",
        r"\b(?:Proceedings of|Journal of)\s+([A-Z][A-Za-z0-9,&\-\s]{3,}?)(?:\.|,|;|$)",
        r"\(([A-Za-z][A-Za-z0-9,&\-\s]{2,})\)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip()
    return ""


def _infer_category_from_problem(text):
    text = _text(text).lower()

    patterns = {
        "tracking & pose estimation": r"\b(track|tracking|localize|localization|pose\s*estimat(e|ion)|estimate\s*pose)\b",
        "detection": r"\b(detect|detection|detecting|identify|identification)\b",
        "classification": r"\b(classify|classification|categorize|recognize|recognition)\b",
        "monitoring & health assessment": r"\b(monitor|monitoring|assess|assessment|health|condition|behavior\s*monitoring)\b",
    }

    for category, pattern in patterns.items():
        if re.search(pattern, text):
            return category

    return ""

def normalize_category(row):
    """
    Normalize the Category column based on patterns.
    If Category is blank, infer from Research Problem (already handled).
    If Category exists, check if it matches any group and normalize.
    """
    patterns = {
        "tracking & pose estimation": r"\b(track|tracking|localize|localization|pose\s*estimat(e|ion)|estimate\s*pose)\b",
        "detection": r"\b(detect|detection|detecting|identify|identification)\b",
        "classification": r"\b(classify|classification|categorize|recognize|recognition)\b",
        "monitoring & health assessment": r"\b(monitor|monitoring|assess|assessment|health|condition|behavior\s*monitoring)\b",
    }

    current = str(row.get("Category", "")).lower()

    for group, pattern in patterns.items():
        if re.search(pattern, current):
            return group  # normalize to canonical group name

    # return original if no match
    return row.get("Category", "")

def _find_column_index(headers, candidates):
    normalized = {_normalize_header(h): idx + 1 for idx, h in enumerate(headers)}
    for candidate in candidates:
        candidate_key = _normalize_header(candidate)
        if candidate_key in normalized:
            return normalized[candidate_key]
    return None
def build_main_csv(
    input_path=SOURCE_WORKBOOK_PATH,
    output_path=MAIN_CSV_PATH,
):
    workbook = openpyxl.load_workbook(input_path)

    missing_sheets = [name for name in SOURCE_SHEETS if name not in workbook.sheetnames]
    if missing_sheets:
        raise ValueError(f"Missing required sheets (case-sensitive): {missing_sheets}")

    column_candidates = {
        "Papers": ["Papers", "Paper", "Title"],
        "Authors": ["Authors", "Author"],
        "Year": ["Year", "Publication Year"],
        "Venue Name": ["Venue Name", "Venue"],
        "Data modality": ["Data modality", "Data Modality", "Modality", "Data Type"],
        "Pass/Fail": ["Pass/Fail", "Pass Fail"],
        "Search Keyword": ["Search Keyword", "Search Keywords", "Keyword", "Keywords"],
        "Approach (AI)": ["Approach (AI)", "Approach", "AI Approach", "Method", "Methodology"],
        "Abstract": ["Abstract", "Summary"],
        "Research Problem": ["Research Problem", "Problem", "Research Task"],
        "Category": ["Category", "Categories"],
    }

    merged_rows = []

    for sheet_name in SOURCE_SHEETS:
        sheet = workbook[sheet_name]
        headers = [cell.value for cell in sheet[1]]

        paper_idx = _find_column_index(headers, column_candidates["Papers"])
        year_idx = _find_column_index(headers, column_candidates["Year"])
        if paper_idx is None or year_idx is None:
            raise ValueError(
                f"Sheet '{sheet_name}' must contain Paper/Title and Year columns."
            )

        resolved_indices = {
            col: _find_column_index(headers, candidates)
            for col, candidates in column_candidates.items()
        }

        papers_idx = resolved_indices.get("Papers")

        for row_idx in range(2, sheet.max_row + 1):
            row = {}
            row_has_values = False
            papers_url = None

            for out_col in OUTPUT_COLUMNS:
                col_idx = resolved_indices.get(out_col)
                cell = sheet.cell(row=row_idx, column=col_idx) if col_idx else None
                value = cell.value if cell else None
                row[out_col] = value
                if value not in (None, ""):
                    row_has_values = True

            if papers_idx:
                papers_cell = sheet.cell(row=row_idx, column=papers_idx)
                if papers_cell.hyperlink is not None:
                    papers_url = papers_cell.hyperlink.target

            row["URL"] = papers_url or ""

            if not row_has_values:
                continue

            # row["Papers"] = _text(row["Papers"])
            # if _should_ignore_by_title(row["Papers"]):
            #     continue

            row["Authors"] = _text(row["Authors"])
            if not row["Authors"]:
                continue

            row["Year"] = _coerce_year_for_output(row["Year"])
            row["Abstract"] = _text(row["Abstract"])
            row["Data modality"] = _text(row["Data modality"])
            row["Search Keyword"] = _text(row["Search Keyword"])
            row["Approach (AI)"] = _text(row["Approach (AI)"])
            row["Research Problem"] = _text(row["Research Problem"])
            row["Category"] = _text(row["Category"])

            # if _should_ignore_by_pass_fail(row["Pass/Fail"]):
            #     continue

            #row["Pass/Fail"] = _normalize_pass_fail(row["Pass/Fail"])
            row["Venue Name"] = _extract_venue_name(row["Venue Name"], row["Papers"])

            if row["Category"]:
                row["Category"] = normalize_category(row)
            else:
                inferred = _infer_category_from_problem(row["Research Problem"])
                if inferred:
                    row["Category"] = inferred

            merged_rows.append(row)

    unique_rows = {}
    for row in merged_rows:
        dedupe_key = (_text(row.get("Papers")).lower(), _to_int_year(row.get("Year")))
        if dedupe_key not in unique_rows:
            unique_rows[dedupe_key] = row

    final_rows = list(unique_rows.values())
    final_rows.sort(
        key=lambda item: (
            -_to_int_year(item.get("Year")),
            _text(item.get("Papers")).lower(),
        )
    )

    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(output_path, "w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(final_rows)

    return output_path