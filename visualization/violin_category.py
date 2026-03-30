import plotly.express as px

from const import CATEGORY_COLORS, FALLBACK_CATEGORY_COLOR, OUTPUT_DIR
#------------------------------
# Violin plot function
# -------------------------------
def plot_category_violin(df):
    """
    Create a violin plot showing the distribution of publications per category over the years.
    df: DataFrame with columns ["Year", "Category"]
    """
    # count publications per year per category
    counts = df.groupby(["Year", "Subcategory (ai task)"]).size().reset_index(name="count")

    # Create violin plot
    fig = px.violin(
        counts,
        x="Subcategory (ai task)",
        y="Year",
        color="Subcategory (ai task)",
        color_discrete_map=CATEGORY_COLORS,
        points="all",  # show individual points
        box=True,      # show box inside violin
        title="Publication Counts per Category Over Years"
    )

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis_title="Subcategory (ai task)",
        yaxis_title="Year",
        showlegend=False,
        height=600,
        width=1000,
        margin=dict(t=100, b=150)
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.write_image(OUTPUT_DIR / "violin_category.pdf")
