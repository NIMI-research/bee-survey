import pandas as pd
import plotly.graph_objects as go

from const import CATEGORY_COLORS, FALLBACK_CATEGORY_COLOR, OUTPUT_DIR


def count_category_over_years(df):
    df = df.copy()
    df["Subcategory (ai task)"] = df["Subcategory (ai task)"].fillna("other").replace("", "other")
    # Aggregate counts per year and category
    data = df.groupby(["Year", "Subcategory (ai task)"]).size().reset_index(name="count")
    years = sorted(data["Year"].unique())
    categories = list(df["Subcategory (ai task)"].unique())
 
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
                opacity=0.9,
                name=cat,
                line=dict(
                    color=CATEGORY_COLORS.get(cat, FALLBACK_CATEGORY_COLOR),
                    shape="spline",
                    smoothing=0.55,
                )
            )
        )

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="white",
        plot_bgcolor="white",
        height=800,
        width=1200,
        xaxis=dict(
            tickmode="linear",
            dtick=1,
        ),
        yaxis=dict(
            tickmode="linear",
            dtick=2,
            tickformat="d",
        ),
        legend=dict(
            orientation="h",
            y=-0.1,
            x=0.5,
            xanchor="center",
            yanchor="top",
            font=dict(size=16)
        ),
        margin=dict(t=100, b=150)
    )

    fig.write_image(OUTPUT_DIR / "count_category_over_years.pdf")

