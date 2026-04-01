import plotly.express as px
from const import OUTPUT_DIR, CATEGORY_COLORS, FALLBACK_CATEGORY_COLOR
from utils import apply_legend_border, save_with_plot_border

def plot_category_approach_bubble(df):

    counts = df.groupby(["Subcategory (ai task)", "Approach group"]).size().reset_index(name="count")
    category_color_map = {
        category: CATEGORY_COLORS.get(category, FALLBACK_CATEGORY_COLOR)
        for category in counts["Subcategory (ai task)"].unique()
    }

    fig = px.scatter(
        counts,
        x="Subcategory (ai task)",
        y="Approach group",
        size="count",
        size_max=50,
        color="Subcategory (ai task)",
        color_discrete_map=category_color_map,

    )

    fig.update_layout(
        template="plotly_white",
        title="Category vs Approach Distribution",
        height=600,
        width=1200,
        showlegend=False,
        xaxis=dict(linecolor="#696969", showgrid=False),
        yaxis=dict(linecolor="#696969", showgrid=False),
    )
    apply_legend_border(fig)
    save_with_plot_border(
        fig,
        png_path=OUTPUT_DIR / "category_approach_bubble.png",
        pdf_path=OUTPUT_DIR / "category_approach_bubble.pdf",
    )
