import pandas as pd
import plotly.graph_objects as go
from const import SECONDARY_PALETTE, OUTPUT_DIR
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
    df = df.dropna(subset=["Approach group"])
    df["Approach group"] = df["Approach group"].astype(str).str.strip()
    df["Approach group"] = df["Approach group"].map(_clip_approach_text)
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df = df.dropna(subset=["Year"])
    df["Year"] = df["Year"].astype(int)

    data = df.groupby(["Approach group", "Year"]).size().reset_index(name="count")
    years = sorted(data["Year"].unique())

    # Sort approaches in increasing order (oldest/simplest -> newest), bottom to top
    approach_order = (
        data.groupby("Approach group", as_index=False)
        .agg(latest_year=("Year", "max"))
        .sort_values(["latest_year", "Approach group"], ascending=[True, True])
    )
    approaches = approach_order["Approach group"].tolist()
    n_approaches = len(approaches)

    spacing = 0.75       # tighter than before -> ridges sit closer together
    peak_height = 1.15   # taller than spacing -> peaks poke into the ridge above (the overlap look)

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
        y_max_val = y_values.max() if y_values.max() > 0 else 1
        y_scaled = y_values / y_max_val * (spacing * peak_height)

        # Filled ridge — translucent so overlaps with the ridge below stay legible
        fig.add_trace(
            go.Scatter(
                x=list(years) + list(years)[::-1],
                y=list(y_scaled + y_offset) + [y_offset] * len(years),
                fill="toself",
                fillcolor=color,
                line=dict(color=color, width=1.5, shape="spline", smoothing=0.75),
                opacity=0.55,
                name=approach,
                showlegend=False,
            )
        )
        # Crisp top outline
        fig.add_trace(
            go.Scatter(
                x=years,
                y=list(y_scaled + y_offset),
                mode="lines",
                line=dict(color=color, width=2, shape="spline", smoothing=0.75),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    tickvals = [i * spacing for i in range(n_approaches)]

    fig.update_layout(
        template="plotly_white",
        title=dict(
            text="<b>Distribution of Approaches Over Years</b>",
            font=dict(size=28, family="Arial Black"),
        ),
        paper_bgcolor="white",
        plot_bgcolor="white",
        height=180 + n_approaches * 55,
        width=1500,
        xaxis=dict(
            showgrid=False,
            tickfont=dict(size=18, family="Arial Black"),
            tickmode="array",
            tickvals=years,
            ticktext=[str(y) for y in years],
        ),
        yaxis=dict(
            title=dict(text="Approach Group", font=dict(size=18, family="Arial Black")),
            autorange="min",
            tickmode="array",
            tickvals=tickvals,
            ticktext=approaches,
            showgrid=False,
            ticklabelstandoff=18,
            tickfont=dict(size=16),
            side="left",
        ),
        yaxis2=dict(
            overlaying="y",
            side="right",
            tickmode="array",
            tickvals=tickvals,
            ticktext=approaches,
            tickfont=dict(size=16),
            showgrid=False,
            matches="y",
        ),
        showlegend=False,
        margin=dict(t=100, b=80, l=220, r=220),
        xaxis_showline=True,
        xaxis_linewidth=2,
        xaxis_linecolor="black",
        yaxis_showline=False,
    )
    apply_legend_border(fig)
    save_with_plot_border(
        fig,
        png_path=OUTPUT_DIR / "joyplot_approaches_over_years.png",
        pdf_path=OUTPUT_DIR / "joyplot_approaches_over_years.pdf",
    )