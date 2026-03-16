import pandas as pd
import plotly.express as px
from const import OUTPUT_DIR, CATEGORY_COLORS

def plot_category_approach_heatmap(df):
    counts = df.groupby(["Category", "Approach Group"]).size().reset_index(name="Count")

    pivot = counts.pivot(
        index="Approach Group",
        columns="Category",
        values="Count"
    ).fillna(0)

    brown_to_yellow_scale = [
        CATEGORY_COLORS["tracking & pose estimation"],
        CATEGORY_COLORS["detection"],
        CATEGORY_COLORS["monitoring & health assessment"],
        CATEGORY_COLORS["classification"],
    ]

    fig = px.imshow(
        pivot,
        text_auto=True,
        aspect="auto",
        labels=dict(x="Category", y="Approach Group", color="Papers"),
        color_continuous_scale=brown_to_yellow_scale,
    )

    fig.update_layout(
        template="plotly_white",
        height=600,
        width=1000
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    
    fig.write_image(OUTPUT_DIR / "category_approach_heatmap.pdf")
