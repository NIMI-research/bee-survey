import plotly.express as px
from const import OUTPUT_DIR, CATEGORY_COLORS, FALLBACK_CATEGORY_COLOR

def plot_category_approach_bubble(df):

    counts = df.groupby(["Category", "Approach Group"]).size().reset_index(name="Count")
    category_color_map = {
        category: CATEGORY_COLORS.get(category, FALLBACK_CATEGORY_COLOR)
        for category in counts["Category"].unique()
    }

    fig = px.scatter(
        counts,
        x="Category",
        y="Approach Group",
        size="Count",
        size_max=50,
        color="Category",
        color_discrete_map=category_color_map,
    )

    fig.update_layout(
        template="plotly_white",
        height=600,
        width=1000,
        showlegend=False,
    )

    
    fig.write_image(OUTPUT_DIR / "category_approach_bubble.pdf")
