import math
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from const import CATEGORY_COLORS, FALLBACK_CATEGORY_COLOR, OUTPUT_DIR, YEAR_CATEGORY_PDF_PATH


def plot_yearly_category_pies(df):

    data = df.groupby(["Year", "Category"]).size().reset_index(name="count")
    years = sorted(data["Year"].unique())

    cols = 5
    rows = math.ceil(len(years) / cols)

    fig = make_subplots(
        rows=rows,
        cols=cols,
        specs=[[{"type": "domain"}]*cols for _ in range(rows)],
        subplot_titles=[str(y) for y in years]
    )

    for i, year in enumerate(years):
        subset = data[data["Year"] == year]
        colors = [CATEGORY_COLORS.get(cat, FALLBACK_CATEGORY_COLOR) for cat in subset["Category"]]

        row = i // cols + 1
        col = i % cols + 1

        fig.add_trace(
            go.Pie(
                labels=subset["Category"],
                values=subset["count"],
                textinfo="percent",
                marker=dict(colors=colors),
                showlegend=True  # legend only once
            ),
            row=row,
            col=col
        )

    fig.update_layout(
        title="Category Distribution per Year",
        height=300 * rows
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.write_image(YEAR_CATEGORY_PDF_PATH)
    fig.show()