import pandas as pd
import plotly.express as px
from const import OUTPUT_DIR, CATEGORY_COLORS

def plot_category_approach_heatmap(df):
    counts = df.groupby(["Subcategory (ai task)", "Approach group"]).size().reset_index(name="count")

    pivot = counts.pivot(
        index="Approach group",
        columns="Subcategory (ai task)",
        values="count"
    ).fillna(0)

    brown_to_yellow_scale = [
        CATEGORY_COLORS["Tracking & Pose Estimation"],
        CATEGORY_COLORS["Detection"],
        CATEGORY_COLORS["Monitoring & Health Assessment"],
        CATEGORY_COLORS["Classification"],
    ]

    fig = px.imshow(
        pivot,
        text_auto=True,
        aspect="auto",
        labels=dict(x="Subcategory (ai task)", y="Approach group", color="Papers"),
        color_continuous_scale=brown_to_yellow_scale,
    )

    fig.update_layout(
        template="plotly_white",
        height=600,
        width=1200
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    
    fig.write_image(OUTPUT_DIR / "category_approach_heatmap.pdf")
