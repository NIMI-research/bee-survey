import plotly.graph_objects as go

from const import OUTPUT_DIR, CATEGORY_COLORS, FALLBACK_CATEGORY_COLOR


def _hex_to_rgba(hex_color, alpha):
    color = hex_color.lstrip("#")
    if len(color) != 6:
        return f"rgba(127,127,127,{alpha})"
    r = int(color[0:2], 16)
    g = int(color[2:4], 16)
    b = int(color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

def plot_category_approach_sankey(df):

    counts = df.groupby(["Subcategory (ai task)", "Approach group"]).size().reset_index(name="count")

    categories = list(df["Subcategory (ai task)"].unique())
    approaches = list(df["Approach group"].unique())

    labels = categories + approaches
    category_node_colors = [CATEGORY_COLORS.get(category, FALLBACK_CATEGORY_COLOR) for category in categories]
    approach_node_colors = ["#D9D9D9"] * len(approaches)
    node_colors = category_node_colors + approach_node_colors

    source = counts["Subcategory (ai task)"].apply(lambda x: categories.index(x))
    target = counts["Approach group"].apply(lambda x: approaches.index(x) + len(categories))
    value = counts["count"]
    link_colors = counts["Subcategory (ai task)"].apply(
        lambda category: _hex_to_rgba(CATEGORY_COLORS.get(category, FALLBACK_CATEGORY_COLOR), 0.35)
    )

    fig = go.Figure(go.Sankey(
        node=dict(
            label=labels,
            pad=15,
            thickness=20,
            color=node_colors
        ),
        link=dict(
            source=source,
            target=target,
            value=value,
            color=link_colors
        )
    ))

    fig.update_layout(
        template="plotly_white",
        height=600,
        width=1000
    )
    fig.write_image(OUTPUT_DIR / "category_approach_sankey.pdf")

    
