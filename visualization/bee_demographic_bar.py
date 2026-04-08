import pandas as pd
import plotly.graph_objects as go

from const import SECONDARY_PALETTE, FALLBACK_CATEGORY_COLOR, INPUT_DIR, OUTPUT_DIR
from utils import apply_legend_border, save_with_plot_border


def plot_bar_bee_demographic(df):
    df = df.copy()

    country_col = next(
        (col for col in ("research_country", "Research_country") if col in df.columns),
        None,
    )
    if country_col is None:
        raise ValueError("Missing required column for bar chart: research_country")

    df["research_country"] = df[country_col].fillna("").astype(str).str.strip()
    df = df[df["research_country"].ne("") & df["research_country"].ne("-")]

    if df.empty:
        return

    data = (
        df.groupby("research_country")
        .size()
        .reset_index(name="count")
        .sort_values(["count", "research_country"], ascending=[False, True])
    )
    total_papers = int(data["count"].sum())
    ordered_countries = data["research_country"].tolist()
    display_countries = [
        country.split(",", 1)[0].strip() if "," in country else country
        for country in ordered_countries
    ]

    n_rows = len(data)

    # ── Alternating row band shapes ──────────────────────────────────────────
    # Rows are rendered top-to-bottom (index 0 = top after autorange="reversed")
    band_shapes = []
    for i in range(n_rows):
        if i % 2 == 0:
            band_shapes.append(
                dict(
                    type="rect",
                    xref="paper", yref="y",
                    x0=0, x1=1,
                    # Each band spans ±0.5 around the row's y-index position
                    y0=i - 0.5, y1=i + 0.5,
                    fillcolor="rgba(245, 235, 220, 0.55)",  # warm beige
                    line_width=0,
                    layer="below",
                )
            )

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=data["count"],
            y=data["research_country"],
            orientation="h",
            width=0.82,
            marker=dict(color=SECONDARY_PALETTE[3]),
            text=data["count"],
            textposition="outside",
            texttemplate="%{x}",
            cliponaxis=False,
        )
    )

    fig.update_layout(
        title=dict(
            text="<b>Countries Where AI Bee Research Is Conducted</b>",
            font=dict(size=39, family="Arial Black"),
        ),
        template="plotly_white",
        height=1000,
        width=1100,
        shapes=band_shapes,
        xaxis=dict(
            side="top",
            tickformat="d",
            tick0=0,
            dtick=2,
            showgrid=False,
            zeroline=False,
        ),
        yaxis=dict(
            categoryorder="array",
            categoryarray=ordered_countries,
            autorange="reversed",
            showgrid=False,          # ← removed horizontal grid lines
            ticklabelstandoff=12,    # ← gap between y-tick labels and the axis/bars
            domain=[0.0, 0.94],
            tickmode="array",
            tickvals=ordered_countries,
            ticktext=display_countries,
            tickfont=dict(size=15, family="Arial Black"),
        ),
        margin=dict(l=240,r=80, t=110, b=60),   # wider l for the standoff gap
        uniformtext=dict(mode="hide", minsize=10),
        font=dict(size=13, family="Arial Black"),
        bargap=0.75,
    )

    fig.update_traces(
        # ── Italic dark-brown count labels ──────
        #first color from plotly spectral palette that is orange
        textfont=dict(size=12, color="#4a2c0a", style="italic"),
        hovertemplate="Country: %{y}<br>Count: %{x}<extra></extra>",
    )
    apply_legend_border(fig)
    save_with_plot_border(
        fig,
        png_path=OUTPUT_DIR / "bar_bee_demographic.png",
        pdf_path=OUTPUT_DIR / "bar_bee_demographic.pdf",
    )