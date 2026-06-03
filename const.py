from pathlib import Path
import plotly.express as px

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
    "Classification": "#FFE926", #originally "#D7CCC8"
    "Monitoring & Health Assessment": "#FBC02D",
}

FALLBACK_CATEGORY_COLOR = "#7f7f7f"

# ===================== PRIMARY PALETTES =====================

SECONDARY_PAL = [
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

# For backwards compatibility
SECONDARY_PALETTE = SECONDARY_PAL

# Spectral palette for choropleth and heatmap visualizations
SPECTRAL_PAL = [
    '#3288bd',  # Dark blue
    '#66c2a5',  # Teal
    '#88d1a7',  # Soft teal-green
    '#abdda4',  # Light green
    '#c8e99f',  # Lime tint
    '#e6f598',  # Pale yellow-green
    '#f3fa8c',  # Lemon yellow-green
    "#fefe8b",  # Light yellow-orange
    '#fee45f',  # Warm yellow
    "#fed400",  # Light cream (center)
    '#fee090',  # Light yellow
    '#f7bc66',  # Amber
    "#ee9943",  # Orange
    '#f46d43',  # Orange-red
    '#d53e4f',  # Dark red
]

# Migration diagram palette combining brown and yellow-orange sequences
MIGRATION_PAL = list(px.colors.sequential.Brwnyl) + list(px.colors.sequential.YlOrBr)

# Word cloud palette with bronze and gold tones
WORDCLOUD_PAL = ["#CD7F32", "#DBAC60", "#FFD700", "#FFA500", "#714106"]


