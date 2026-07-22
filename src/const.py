from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
VISUALIZATION_DIR = BASE_DIR / "visualization"

SOURCE_WORKBOOK_PATH = INPUT_DIR / "Bee-Me Literature Review.xlsx"
MAIN_CSV_PATH = INPUT_DIR / "Bee-Me Literature Review_Main.csv"
VISUALIZATION_CSV_PATH = INPUT_DIR / "Visualization.csv"


CATEGORY_COLORS = {
    "Tracking & Pose Estimation": "#6D4C41",
    "Detection": "#A1887F",
    "Classification": "#FFE926", #originally "#D7CCC8"
    "Monitoring & Predictive Health Analytics": "#FBC02D",
}

FALLBACK_CATEGORY_COLOR = "#7f7f7f"

SECONDARY_PALETTE = [
    "#78350F",  # espresso
    "#A16207",  # olive gold
    "#B45309",  # deep amber
    "#D97706",  # warm gold
    "#F59E0B",  # honey yellow
    "#FBBF24",  # bright amber
    "#FCD34D",  # soft golden
    "#FDE68A",  # pale honey
    "#DAB308",  # golden
    "#A16207",  # olive gold
    "#B7791F",  # toasted amber
]


