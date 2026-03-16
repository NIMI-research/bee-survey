from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
VISUALIZATION_DIR = BASE_DIR / "visualization"

SOURCE_WORKBOOK_PATH = INPUT_DIR / "Bee-Me Literature Review.xlsx"
MAIN_CSV_PATH = INPUT_DIR / "Bee-Me Literature Review_Main.csv"

CATEGORY_COLORS = {
    "tracking & pose estimation": "#6D4C41",
    "detection": "#A1887F",
    "classification": "#FFE226", #originally "#D7CCC8"
    "monitoring & health assessment": "#FBC02D",
}

FALLBACK_CATEGORY_COLOR = "#7f7f7f"
