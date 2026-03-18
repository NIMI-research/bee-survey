from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
VISUALIZATION_DIR = BASE_DIR / "visualization"

SOURCE_WORKBOOK_PATH = INPUT_DIR / "Bee-Me Literature Review.xlsx"
MAIN_CSV_PATH = INPUT_DIR / "Bee-Me Literature Review_Main.csv"
VISUALIZATION_CSV_PATH = INPUT_DIR / "Visualization.csv"

CATEGORY_COLORS = {
    "Tracking & Pose Estimation": "#6D4C41",
    "Detection": "#A1887F",
    "Classification": "#FFE226", #originally "#D7CCC8"
    "Monitoring & Health Assessment": "#FBC02D",
}

FALLBACK_CATEGORY_COLOR = "#7f7f7f"
