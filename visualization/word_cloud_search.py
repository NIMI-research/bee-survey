"""Keyword word cloud generator using an ellipse mask."""

from __future__ import annotations

from pathlib import Path
import random
import numpy as np
from PIL import Image, ImageDraw
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from const import OUTPUT_DIR, WORDCLOUD_PAL
from utils import save_with_plot_border

# ============================================================================
# CONFIGURATION (update as needed)
# ============================================================================


def _color_func(word, font_size, position, orientation, random_state=None, **kwargs):
    return random.choice(WORDCLOUD_PAL)




# ============================================================================
# MAIN WORDCLOUD FUNCTION
# ============================================================================

def _build_ellipse_mask(width: int, height: int) -> np.ndarray:
    """Build a WordCloud-compatible ellipse mask."""
    img = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(img)
    margin_x = int(width * 0.04)
    margin_y = int(height * 0.06)
    draw.ellipse((margin_x, margin_y, width - margin_x, height - margin_y), fill=0)
    return np.array(img)


def plot_keyword_wordcloud(
    df,
    *,
    # Canvas --------------------------------------------------------------
    width: int = 2400,
    height: int = 1600,
    background_color: str = "#FFFFFF",
    # Typography ----------------------------------------------------------
    min_font_size: int = 25,
    max_font_size: int = 250,
    prefer_horizontal: float = 0.75,
    # Output --------------------------------------------------------------
    output_name: str = "keyword_wordcloud",
) -> None:
    """
    Generate a keyword word cloud using an ellipse mask.

    - Font:   Georgia (hardcoded)
    - Shape:  Ellipse
    - Colors: Driven by SECONDARY_PALETTE

    Parameters
    ----------
    df : DataFrame
        DataFrame with "Search keyword" column
    """

    # 1. Extract and clean keywords ----------------------------------------
    keywords = (
        df["Search keyword"]
        .fillna("")
        .astype(str)
        .str.replace(r"[\r\n]+", " ", regex=True)
        .str.strip()
    )
    keywords = keywords[keywords != ""]
    freq = keywords.value_counts().to_dict()

    # 2. Create ellipse mask =============================================
    mask = _build_ellipse_mask(width=width, height=height)

    # 3. Find font ========================================================
    font_path = fm.findfont(fm.FontProperties(family="Georgia"))

    # 4. Build word cloud =================================================
    wc = WordCloud(
        width=width,
        height=height,
        background_color=background_color,
        mask=mask,
        contour_width=0,
        color_func=_color_func,
        font_path=font_path,
        min_font_size=min_font_size,
        max_font_size=max_font_size,
        scale=2,
        prefer_horizontal=prefer_horizontal,
        repeat=False,
        collocations=False,
        margin=4,
        relative_scaling=0.55,
    ).generate_from_frequencies(freq)

    # 5. Plot =============================================================
    fig_w = mask.shape[1] / 200
    fig_h = mask.shape[0] / 200

    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=300)
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    fig.patch.set_facecolor(background_color)
    ax.set_facecolor(background_color)
    fig.suptitle("Search Keywords Word Cloud", fontsize=24, weight="bold", y=0.98)
    plt.subplots_adjust(left=0, right=1, top=0.95, bottom=0)

    # 6. Save =============================================================
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{output_name}.pdf"
    out_path_png = OUTPUT_DIR / f"{output_name}.png"
    
    save_with_plot_border(
        fig,
        png_path=out_path_png,
        pdf_path=out_path,
        facecolor=background_color,
        dpi=300,
        bbox_inches="tight",
        pad_inches=0.1,
    )
    plt.close(fig)

