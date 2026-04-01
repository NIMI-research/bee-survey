from __future__ import annotations

from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw
from wordcloud import WordCloud

from const import OUTPUT_DIR, SECONDARY_PALETTE
from utils import save_with_plot_border


# ---------------------------------------------------------------------------
# Colour function — driven by SECONDARY_PALETTE imported from const
# ---------------------------------------------------------------------------

def _color_func(word, font_size, position, orientation, random_state=None, **kwargs):
    import random
    return random.choice(SECONDARY_PALETTE)


# ---------------------------------------------------------------------------
# Mask helpers
# ---------------------------------------------------------------------------

def _make_ellipse_mask(width: int, height: int) -> np.ndarray:
    """
    Tight ellipse that fills almost the whole canvas.
    WordCloud convention: 255 = forbidden area, 0 = word fill area.
    """
    img = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(img)
    pad = 40
    draw.ellipse([pad, pad, width - pad, height - pad], fill=0)
    return np.array(img)


def _load_bee_mask(path: Path) -> np.ndarray | None:
    """
    Load a silhouette PNG → WordCloud-compatible mask (0 = fill, 255 = forbidden).
    Auto-inverts images that have a light background (the common case).
    Returns None + warning if the file is missing.
    """
    if not path.exists():
        print(f"[wordcloud] Mask not found: {path} – falling back to ellipse.")
        return None

    img = Image.open(path).convert("RGBA")

    # Composite onto white to flatten any transparency
    bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
    bg.paste(img, mask=img.split()[3])
    grey = np.array(bg.convert("L"))

    # If corners are light → shape is dark on white → invert so shape = 0 (fill)
    corners = [grey[0, 0], grey[0, -1], grey[-1, 0], grey[-1, -1]]
    if np.mean(corners) > 128:
        grey = 255 - grey

    return np.where(grey < 128, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Main plotting function
# ---------------------------------------------------------------------------

def plot_keyword_wordcloud(
    df,
    *,
    # Shape ---------------------------------------------------------------
    use_bee_mask: bool = False,
    bee_mask_path: Path = Path("input/bee.jpeg"),
    # Canvas --------------------------------------------------------------
    width: int = 2400,
    height: int = 1600,
    background_color: str = "#FFFFFF",
    # Typography ----------------------------------------------------------
    min_font_size: int = 12,
    max_font_size: int = 280,
    prefer_horizontal: float = 0.65,
    # Output --------------------------------------------------------------
    output_name: str = "keyword_wordcloud",
) -> None:
    """
    Generate a professional keyword word cloud.

    - Font:   Georgia (hardcoded)
    - Shape:  Tight ellipse by default; optional bee silhouette
    - Colors: Driven by SECONDARY_PALETTE from const.py

    Quick examples
    --------------
    # Ellipse (default):
    plot_keyword_wordcloud(df)

    # Bee silhouette:
    plot_keyword_wordcloud(df, use_bee_mask=True)

    # Custom bee path:
    plot_keyword_wordcloud(df, use_bee_mask=True, bee_mask_path=Path("assets/bee.png"))
    """

    # 1. Frequencies -------------------------------------------------------
    keywords = (
        df["Search keyword"]
        .fillna("")
        .astype(str)
        .str.replace(r"[\r\n]+", " ", regex=True)
        .str.strip()
    )
    keywords = keywords[keywords != ""]
    freq = keywords.value_counts().to_dict()

    if not freq:
        print("[wordcloud] No keywords found – nothing to plot.")
        return

    # 2. Mask --------------------------------------------------------------
    if use_bee_mask:
        mask = _load_bee_mask(bee_mask_path) or _make_ellipse_mask(width, height)
    else:
        mask = _make_ellipse_mask(width, height)

    # 3. Font — hardcoded Georgia ------------------------------------------
    font_path = fm.findfont(fm.FontProperties(family="Georgia"))
    print(f"[wordcloud] Font: {font_path}")

    # 4. Build cloud -------------------------------------------------------
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

    # 5. Plot --------------------------------------------------------------
    fig_w = mask.shape[1] / 200
    fig_h = mask.shape[0] / 200

    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=300)
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    fig.patch.set_facecolor(background_color)
    ax.set_facecolor(background_color)
    fig.suptitle("Search Keywords Word Cloud", fontsize=24, weight="bold", y=0.98)
    plt.subplots_adjust(left=0, right=1, top=0.95, bottom=0)

    # 6. Save --------------------------------------------------------------
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
    print(f"[wordcloud] Saved → {out_path}")