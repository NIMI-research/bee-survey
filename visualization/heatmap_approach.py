import pandas as pd
import plotly.express as px

from const import OUTPUT_DIR, SECONDARY_PALETTE


def _clip_category_text(text, max_words=5):
    if not text:
        return text
    if "—" in text:
        text = text.split("—", 1)[0].strip()
    words = text.split()
    if len(words) > max_words:
        return " ".join(words[:max_words])
    return text


def heatmap_subcat_approach_by_category(df):
    df = df.copy()

    # Clean columns
    df["Category (section)"] = df["Category (section)"].fillna("other").replace("", "other")
    df["Category (section)"] = df["Category (section)"].map(_clip_category_text)
    df["Subcategory (ai task)"] = df["Subcategory (ai task)"].fillna("other").replace("", "other")
    df["Approach group"] = df["Approach group"].fillna("other").replace("", "other")

    # Aggregate counts
    data = (
        df.groupby(["Category (section)", "Subcategory (ai task)", "Approach group"])
        .size()
        .reset_index(name="count")
    )

    # Normalize to percentages within each (Category (section), Subcategory)
    data["percent"] = data.groupby(
        ["Category (section)", "Subcategory (ai task)"]
    )["count"].transform(lambda x: x / x.sum())

    # Plot
    fig = px.density_heatmap(
        data,
        x="Subcategory (ai task)",
        y="Approach group",
        z="percent",
        facet_col="Category (section)",
        histfunc="avg",  # we already aggregated
        color_continuous_scale=SECONDARY_PALETTE,
        labels={
            "Subcategory (ai task)": "Subcategory",
            "Approach group": "Approach",
            "Category (section)": "Category",
            "percent": "Share",
        },
    )

    fig.update_layout(
        template="plotly_white",
        height=800,
        width=2000,
        coloraxis_colorbar=dict(
            title="Share",
            tickformat=".0%"
        ),
        margin=dict(t=100, b=100)
    )

    fig.update_xaxes(
        tickangle=45,
        showgrid=True,
        gridcolor="lightgray",
        gridwidth=1,
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="lightgray",
        gridwidth=1,
    )

    # Remove repeated axis titles on every facet and clean facet labels.
    fig.for_each_xaxis(lambda axis: axis.update(title_text=""))
    fig.for_each_yaxis(lambda axis: axis.update(title_text=""))
    fig.for_each_annotation(
        lambda ann: ann.update(text=ann.text.replace("Category=", ""))
    )

    fig.write_image(OUTPUT_DIR / "heatmap_subcat_approach_by_category.pdf")