from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

BORDER_COLOR = "#4A2C0A"
BORDER_WIDTH = 5
IMAGE_BORDER_INSET_PX = 8
IMAGE_BORDER_RADIUS_PX = 20
IMAGE_OUTER_MARGIN_PX = 26


def _plotly_has_visible_legend(fig) -> bool:
    layout_showlegend = getattr(fig.layout, "showlegend", None)
    if layout_showlegend is False:
        return False

    if len(fig.data) == 0:
        return bool(layout_showlegend)

    for trace in fig.data:
        trace_showlegend = getattr(trace, "showlegend", None)
        if trace_showlegend is False:
            continue
        return True
    return False


def _add_rounded_border_to_image(
    input_path: Path,
    output_path: Path,
    *,
    color: str = BORDER_COLOR,
    width: float = BORDER_WIDTH,
    inset_px: int = IMAGE_BORDER_INSET_PX,
    radius_px: int = IMAGE_BORDER_RADIUS_PX,
    outer_margin_px: int = IMAGE_OUTER_MARGIN_PX,
) -> None:
    with Image.open(input_path).convert("RGBA") as image:
        draw = ImageDraw.Draw(image)
        x0 = inset_px
        y0 = inset_px
        x1 = max(x0 + 1, image.width - inset_px - 1)
        y1 = max(y0 + 1, image.height - inset_px - 1)
        radius = max(0, min(radius_px, (x1 - x0) // 2, (y1 - y0) // 2))
        draw.rounded_rectangle(
            [x0, y0, x1, y1],
            radius=radius,
            outline=color,
            width=max(1, int(round(width))),
        )

        margin = max(0, int(outer_margin_px))
        if margin > 0:
            expanded = Image.new(
                "RGBA",
                (image.width + margin * 2, image.height + margin * 2),
                (255, 255, 255, 255),
            )
            expanded.paste(image, (margin, margin))
            expanded.save(output_path)
            return

        image.save(output_path)


def _export_plotly_to_png(fig, temp_png_path: Path, scale: int) -> None:
    fig.write_image(temp_png_path, scale=scale)


def _export_matplotlib_to_png(
    fig,
    temp_png_path: Path,
    *,
    facecolor: str,
    dpi: int,
    bbox_inches: str | None,
    pad_inches: float,
) -> None:
    save_kwargs = {
        "dpi": dpi,
        "facecolor": facecolor,
    }
    if bbox_inches is not None:
        save_kwargs["bbox_inches"] = bbox_inches
        save_kwargs["pad_inches"] = pad_inches
    fig.savefig(temp_png_path, **save_kwargs)


def apply_legend_border(
    fig,
    *,
    color: str = BORDER_COLOR,
    width: float = 3,
    bg_color: str = "rgba(255,255,255,0.68)",
) -> None:
    if not _plotly_has_visible_legend(fig):
        return

    fig.update_layout(
        legend=dict(
            bordercolor=color,
            borderwidth=width,
            bgcolor=bg_color,
        )
    )


def save_with_plot_border(
    fig,
    *,
    png_path: Path,
    pdf_path: Path | None = None,
    scale: int = 2,
    color: str = BORDER_COLOR,
    width: float = BORDER_WIDTH,
    facecolor: str = "white",
    dpi: int = 300,
    bbox_inches: str | None = None,
    pad_inches: float = 0.1,
) -> None:
    png_path = Path(png_path)
    png_path.parent.mkdir(parents=True, exist_ok=True)

    temp_png_path = png_path.with_name(f"{png_path.stem}__tmp_noborder.png")

    if hasattr(fig, "write_image"):
        _export_plotly_to_png(fig, temp_png_path, scale=scale)
    elif hasattr(fig, "savefig"):
        _export_matplotlib_to_png(
            fig,
            temp_png_path,
            facecolor=facecolor,
            dpi=dpi,
            bbox_inches=bbox_inches,
            pad_inches=pad_inches,
        )
    else:
        raise TypeError("Unsupported figure object. Expected Plotly or Matplotlib figure.")

    _add_rounded_border_to_image(
        temp_png_path,
        png_path,
        color=color,
        width=width,
    )

    if pdf_path is not None:
        pdf_path = Path(pdf_path)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(png_path).convert("RGB") as image:
            image.save(pdf_path, "PDF", resolution=300.0)

    if temp_png_path.exists():
        temp_png_path.unlink()
