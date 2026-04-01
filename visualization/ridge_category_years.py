import pandas as pd
import plotly.graph_objects as go
from const import SECONDARY_PALETTE, OUTPUT_DIR, SECONDARY_PALETTE
from utils import apply_legend_border, save_with_plot_border


def _clip_approach_text(text, max_words=5):
    """Clip approach text at em dash or limit to max_words."""
    if not text:
        return text
    if "—" in text:
        text = text.split("—")[0].strip()
    words = text.split()
    if len(words) > max_words:
        text = " ".join(words[:max_words])
    return text


def ridge_plot_approaches_over_years(df):
    df = df.copy()

    # Clean columns
    df["Approach group"] = df["Approach group"].fillna("other").replace("", "other")
    df["Approach group"] = df["Approach group"].map(lambda x: _clip_approach_text(x))
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df = df.dropna(subset=["Year"])
    df["Year"] = df["Year"].astype(int)

    if df.empty:
        return

    # Aggregate counts per approach per year
    data = df.groupby(["Approach group", "Year"]).size().reset_index(name="count")

    approaches = sorted(data["Approach group"].unique())
    years = sorted(data["Year"].unique())

    n_approaches = len(approaches)
    spacing = 1.0  # vertical spacing between ridges

    fig = go.Figure()

    for idx, approach in enumerate(approaches):
        cat_data = (
            data[data["Approach group"] == approach]
            .set_index("Year")["count"]
            .reindex(years, fill_value=0)
        )

        y_offset = idx * spacing
        color = SECONDARY_PALETTE[idx % len(SECONDARY_PALETTE)]

        y_values = cat_data.values.astype(float)
        # Normalize within each ridge so they visually fit within spacing
        y_max = y_values.max() if y_values.max() > 0 else 1
        y_scaled = y_values / y_max * (spacing * 0.85)

        # Filled area (ridge)
        fig.add_trace(
            go.Scatter(
                x=list(years) + list(years)[::-1],
                y=list(y_scaled + y_offset) + [y_offset] * len(years),
                fill="toself",
                fillcolor=color,
                line=dict(color=color, width=1.5, shape="spline", smoothing=0.75),
                opacity=0.6,
                name=approach,
                showlegend=True,
            )
        )

        # Top line for clarity
        fig.add_trace(
            go.Scatter(
                x=years,
                y=list(y_scaled + y_offset),
                mode="lines",
                line=dict(color=color, width=2),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    # Y-axis tick labels centered on each ridge
    fig.update_layout(
        template="plotly_white",
        title="Distribution of Approaches Over Years",
        paper_bgcolor="white",
        plot_bgcolor="white",
        height=200 + n_approaches * 80,
        width=1400,
        xaxis=dict(
            title="Year",
            showgrid=False,
            tickfont=dict(size=14),
            tickmode="array",
            tickvals=years,
            ticktext=[str(y) for y in years],
        ),
        yaxis=dict(
            tickmode="array",
            tickvals=[i * spacing + spacing * 0.4 for i in range(n_approaches)],
            ticktext=approaches,
            showgrid=False,
            tickfont=dict(size=13),
        ),
        legend=dict(
            orientation="h",
            y=-0.15,
            x=0.5,
            xanchor="center",
            yanchor="top",
            font=dict(size=14),
        ),
        margin=dict(t=100, b=180, l=200, r=50),
        xaxis_showline=True,
        xaxis_linewidth=2,
        xaxis_linecolor="black",
        yaxis_showline=False,
    )
    apply_legend_border(fig)
    save_with_plot_border(
        fig,
        png_path=OUTPUT_DIR / "ridge_approaches_over_years.png",
        pdf_path=OUTPUT_DIR / "ridge_approaches_over_years.pdf",
    )

