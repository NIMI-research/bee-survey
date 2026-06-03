import pandas as pd
import plotly.graph_objects as go

from const import CATEGORY_COLORS, FALLBACK_CATEGORY_COLOR, OUTPUT_DIR
from utils import apply_legend_border, save_with_plot_border


def count_category_over_years(df):
    df = df.copy()
    df["Subcategory (ai task)"] = df["Subcategory (ai task)"].fillna("other").replace("", "other")
    # Aggregate counts per year and category
    data = df.groupby(["Year", "Subcategory (ai task)"]).size().reset_index(name="count")
    years = sorted(data["Year"].unique())
    categories_raw = list(df["Subcategory (ai task)"].unique())
    detection_categories = [c for c in categories_raw if str(c).strip().lower() == "detection"]
    other_categories = [c for c in categories_raw if str(c).strip().lower() != "detection"]
    categories = detection_categories + other_categories
 
    # Prepare traces for stacked area
    fig = go.Figure()
    for cat in categories:
        cat_data = data[data["Subcategory (ai task)"] == cat].set_index("Year")["count"].reindex(years, fill_value=0)
        fig.add_trace(
            go.Scatter(
                x=years,
                y=cat_data,
                mode="lines",
                stackgroup="one",
                opacity=0.85,
                name=cat,
                line=dict(
                    color=CATEGORY_COLORS.get(cat, FALLBACK_CATEGORY_COLOR),
                    shape="spline",
                    smoothing=0.65,
                )
            )
        )

    fig.update_layout(
        template="plotly_white",
        title="Distribution of Categories over Years",
        font=dict(size=18),
        paper_bgcolor="white",
        plot_bgcolor="white",
        height=600,
        width=800,
        xaxis=dict(
            #title="Year",
            linecolor="#696969",
            linewidth=3,
            showline=True,
            tickmode="linear",
            dtick=1,
            showgrid=False,
            tickfont=dict(size=12, family="Arial Black"),
        ),
        yaxis=dict(
            #title="Count",
            linecolor="#696969",
            linewidth=3,
            showline=True,
            tickmode="linear",
            dtick=2,
            tickformat="d",
            showgrid=False,
            tickfont=dict(size=12, family="Arial Black"),
        ),
        legend=dict(
            orientation="v",
            y=0.97,
            x=0.05,
            xanchor="left",
            yanchor="top",
            font=dict(size=14,family="Arial Black"),
        ),
    )
    apply_legend_border(fig)
    save_with_plot_border(
        fig,
        png_path=OUTPUT_DIR / "count_category_over_years.png",
        pdf_path=OUTPUT_DIR / "count_category_over_years.pdf",
    )

