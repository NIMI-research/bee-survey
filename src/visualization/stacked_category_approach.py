import pandas as pd
import plotly.graph_objects as go

from const import CATEGORY_COLORS, FALLBACK_CATEGORY_COLOR, OUTPUT_DIR, SECONDARY_PALETTE
from utils import apply_legend_border, save_with_plot_border


def _clip_category_text(text, max_words=5):
    """Clip category text at em dash or limit to max_words."""
    if not text:
        return text
    # Split at em dash if present
    if "—" in text:
        text = text.split("—")[0].strip()
    # Limit to max_words
    words = text.split()
    if len(words) > max_words:
        text = " ".join(words[:max_words])
    return text


def _format_xlabel(text, words_per_line=3, max_lines=2):
    """Wrap x-axis labels into at most max_lines, each with words_per_line words."""
    if not text:
        return text

    words = str(text).split()
    wrapped_lines = []
    for line_idx in range(max_lines):
        start = line_idx * words_per_line
        end = start + words_per_line
        if start >= len(words):
            break
        wrapped_lines.append(" ".join(words[start:end]))

    if len(words) > words_per_line * max_lines and wrapped_lines:
        wrapped_lines[-1] = f"{wrapped_lines[-1]}..."

    return "<br>".join(wrapped_lines)


def count_approach_over_category(df):
    df = df.copy()

    # Clean columns
    df["Category (section)"] = df["Category (section)"].fillna("other").replace("", "other")
    df["Category (section)"] = df["Category (section)"].map(lambda x: _clip_category_text(x))
    df["Approach group"] = df["Approach group"].fillna("").astype(str).str.strip()
    df = df[df["Approach group"].ne("") & df["Approach group"].ne("-")]
    if df.empty:
        return

    # Aggregate counts
    data = df.groupby(["Category (section)", "Approach group"]).size().reset_index(name="count")

    categories = sorted(data["Category (section)"].unique())
    approaches = list(data["Approach group"].unique())
    formatted_categories = [_format_xlabel(category) for category in categories]

    fig = go.Figure()

    for idx, app in enumerate(approaches):
        app_data = (
            data[data["Approach group"] == app]
            .set_index("Category (section)")["count"]
            .reindex(categories, fill_value=0)
        )

        fig.add_trace(
            go.Bar(
                x=categories,
                y=app_data,
                name=app,
                marker=dict(
                    color=SECONDARY_PALETTE[idx % len(SECONDARY_PALETTE)]
                ),
                opacity=0.9,
            )
        )

    fig.update_layout(
        barmode="stack",
        template="plotly_white",
        title="Approaches for Tackling Categories of Researach Problems",
        #size of title
        title_font=dict(size=28),
        paper_bgcolor="white",
        plot_bgcolor="white",
        height=900,
        width=1600,
        # xaxis=dict(
        #     tickangle=30,
        #     showgrid=False,
        #     gridwidth=1,
        #     gridcolor="lightgray",
        # ),
        # yaxis=dict(
        #     tickformat="d",
        #     showgrid=True,
        #     gridwidth=1,
        #     gridcolor="lightgray",
        # ),
        xaxis=dict(
            showgrid=False,
            tickfont=dict(size=16, family="Arial Black"),
            tickmode="array",
            tickvals=categories,
            ticktext=formatted_categories,
            tickangle=0,
            automargin=True,
        ),
        yaxis=dict(
            tickformat="d",
            showgrid=False,
            tickfont=dict(size=16, family="Arial Black"),
        ),
        legend=dict(
            orientation="v",
            y=1,
            x=1,
            xanchor="right",
            yanchor="top",
            font=dict(size=20)
        ),
        margin=dict(t=100, b=50),
        xaxis_showline=True,
        xaxis_linewidth=2,
        xaxis_linecolor="black",
        yaxis_showline=True,
        yaxis_linewidth=2,
        yaxis_linecolor="black",
    )
    apply_legend_border(fig)
    save_with_plot_border(
        fig,
        png_path=OUTPUT_DIR / "count_approach_over_category.png",
        pdf_path=OUTPUT_DIR / "count_approach_over_category.pdf",
    )