import pandas as pd
import plotly.graph_objects as go

from const import CATEGORY_COLORS, FALLBACK_CATEGORY_COLOR, OUTPUT_DIR, SECONDARY_PALETTE


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


def count_approach_over_category(df):
    df = df.copy()

    # Clean columns
    df["Category (section)"] = df["Category (section)"].fillna("other").replace("", "other")
    df["Category (section)"] = df["Category (section)"].map(lambda x: _clip_category_text(x))
    df["Approach group"] = df["Approach group"].fillna("other").replace("", "other")

    # Aggregate counts
    data = df.groupby(["Category (section)", "Approach group"]).size().reset_index(name="count")

    categories = sorted(data["Category (section)"].unique())
    approaches = list(df["Approach group"].unique())

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
        paper_bgcolor="white",
        plot_bgcolor="white",
        height=800,
        width=1200,
        xaxis=dict(
            tickangle=30,
            showgrid=True,
            gridwidth=1,
            gridcolor="lightgray",
        ),
        yaxis=dict(
            tickformat="d",
            showgrid=True,
            gridwidth=1,
            gridcolor="lightgray",
        ),
        legend=dict(
            orientation="h",
            y=-0.2,
            x=0.5,
            xanchor="center",
            yanchor="top",
            font=dict(size=16)
        ),
        margin=dict(t=100, b=200),
        xaxis_showline=True,
        xaxis_linewidth=2,
        xaxis_linecolor="black",
        yaxis_showline=True,
        yaxis_linewidth=2,
        yaxis_linecolor="black",
    )

    fig.write_image(OUTPUT_DIR / "count_approach_over_category.pdf")