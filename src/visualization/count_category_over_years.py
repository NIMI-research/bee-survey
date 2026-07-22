import pandas as pd
import plotly.graph_objects as go

from const import FALLBACK_CATEGORY_COLOR, OUTPUT_DIR
from utils import apply_legend_border, save_with_plot_border

CATEGORY_COLORS = {
    "Detection": "#A79A96",
    "Tracking & Pose Estimation": "#8C726E",
    "Monitoring & Predictive Health Analytics": "#F6C04B",
    "Classification": "#FFE55C",
    "other": "#D3D3D3",
}

def count_category_over_years(df):
    df = df.copy()
    df["Subcategory (ai task)"] = df["Subcategory (ai task)"].fillna("other").replace("", "other")
    df["Subcategory (ai task)"] = df["Subcategory (ai task)"].replace(
        "monitoring & predictive health analytics","Monitoring & Predictive Health Analytics"
    )
    df["Subcategory (ai task)"] = df["Subcategory (ai task)"].replace(
        "tracking & pose estimation", "Tracking & Pose Estimation"
    )
    data = df.groupby(["Year", "Subcategory (ai task)"]).size().reset_index(name="count")
    years = sorted(data["Year"].unique())
    categories_raw = list(df["Subcategory (ai task)"].unique())
    detection_categories = [c for c in categories_raw if str(c).strip().lower() == "detection"]
    other_categories = [c for c in categories_raw if str(c).strip().lower() != "detection"]
    categories = detection_categories + other_categories

    max_count = data["count"].max()
    year_totals = data.groupby("Year")["count"].sum().reindex(years, fill_value=0)
    max_total = year_totals.max()
    year_category_counts = data.groupby("Year").size().reindex(years, fill_value=0)

    bargap = 0.15
    half_width = (1 - bargap) / 2  # matches the actual rendered width of each year's bar cluster

    fig = go.Figure()
    for cat in categories:
        cat_data = data[data["Subcategory (ai task)"] == cat].set_index("Year")["count"].reindex(years, fill_value=0)
        bar_labels = [str(value) if value > 0 and year_category_counts[year] > 1 else "" for year, value in zip(years, cat_data)]
        fig.add_trace(
            go.Bar(
                x=years,
                y=cat_data,
                name=cat,
                text=bar_labels,
                textposition="outside",
                cliponaxis=False,
                marker=dict(
                    color=CATEGORY_COLORS.get(cat, FALLBACK_CATEGORY_COLOR),
                    line=dict(width=0.5, color="white"),
                ),
                opacity=1,
            )
        )

    # translucent background block per year, sized to that year's total —
    # sits behind the grouped bars and visually separates one year's cluster from the next
    shapes = []
    annotations = []
    for yr in years:
        total = year_totals[yr]
        shapes.append(
            dict(
                type="rect",
                xref="x", yref="y",
                x0=yr - half_width, x1=yr + half_width,
                y0=0, y1=total,
                #superlight yellowish gray
                fillcolor="rgba(200, 200, 200, 0.5)",
                line=dict(width=0),
                layer="below",
            )
        )
        annotations.append(
            dict(
                x=yr, y=total,
                xref="x", yref="y",
                text=f"<b>{total}</b>",
                showarrow=False,
                yshift=14,  # floats just above the translucent block, using the vertical headroom
                font=dict(size=15, family="Arial Black", color="#696969"),
            )
        )

    fig.update_layout(
        barmode="group",
        bargap=bargap,
        bargroupgap=0.03,
        template="plotly_white",
        paper_bgcolor="white",
        plot_bgcolor="white",
        height=900,
        width=1400,
        shapes=shapes,
        annotations=annotations,
        xaxis=dict(
            title=dict(text="Year", font=dict(size=20, family="Arial Black")),
            linecolor="#696969",
            linewidth=3,
            showline=True,
            tickmode="linear",
            dtick=1,
            showgrid=False,
            tickfont=dict(size=18, family="Arial Black"),
        ),
        yaxis=dict(
            title=dict(text="Count of Papers per Category", font=dict(size=20, family="Arial Black")),
            linecolor="#696969",
            linewidth=3,
            showline=True,
            tickmode="linear",
            dtick=2,
            tickformat="d",
            showgrid=False,
            range=[0, max(max_count, max_total) + 2],  # extra headroom for bar labels and yearly totals
            tickfont=dict(size=18, family="Arial Black"),
        ),
        legend=dict(
            orientation="h",
            y=1.08,
            x=0.08,
            xanchor="left",
            yanchor="top",
            font=dict(size=20, family="Arial"),
        ),
    )
    apply_legend_border(fig)
    save_with_plot_border(
        fig,
        png_path=OUTPUT_DIR / "count_category_over_years.png",
        pdf_path=OUTPUT_DIR / "count_category_over_years_group_stack.pdf",
    )