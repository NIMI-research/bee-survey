import plotly.graph_objects as go
from const import OUTPUT_DIR, CATEGORY_COLORS, FALLBACK_CATEGORY_COLOR, SECONDARY_PALETTE
import pandas as pd


MIDDLE_LINK_SCALE = 1.35
LINK_ALPHA = 0.22


def _hex_to_rgba(hex_color, alpha):
    color = hex_color.lstrip("#")
    if len(color) != 6:
        return f"rgba(127,127,127,{alpha})"
    r = int(color[0:2], 16)
    g = int(color[2:4], 16)
    b = int(color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _normalize_column_name(name):
    return "".join(c.lower() for c in str(name).strip() if c.isalnum())


def _find_column(columns, candidates):
    normalized = {_normalize_column_name(col): col for col in columns}
    for candidate in candidates:
        candidate_key = _normalize_column_name(candidate)
        if candidate_key in normalized:
            return normalized[candidate_key]
    return None



def _prepare_modality_approach_category(df):
    """Return normalized dataframe for modality -> approach -> category plots."""
    df = df.copy()

    modality_col = _find_column(df.columns, ["Data modality", "Data Modality"])
    approach_col = _find_column(df.columns, ["Approach group", "Approach Group"])
    category_col = _find_column(df.columns, ["Category section", "Category (section)", "Category"])

    if not modality_col or not approach_col or not category_col:
        raise KeyError("Required columns missing. Need modality, approach group, and category section columns.")

    def extract_category_section(cat):
        if pd.isna(cat):
            return ""
        cat = str(cat)
        if "— " in cat:
            return cat.split("— ")[0].strip()
        return " ".join(cat.split()[:5]) 

    def is_empty_or_dash(series):
        text = series.fillna("").astype(str).str.strip()
        return text.eq("") | text.str.fullmatch(r"-+", na=False)

    df["Data Modality"] = df[modality_col].fillna("").astype(str).str.split().str[0].str.lower()
    df["Approach group"] = df[approach_col].fillna("").astype(str).str.strip()
    df["Category section"] = df[category_col].apply(extract_category_section)

    invalid_rows = (
        is_empty_or_dash(df["Data Modality"])
        | is_empty_or_dash(df["Approach group"])
        | is_empty_or_dash(df["Category section"])
    )
    df = df[~invalid_rows].copy()
    return df

def plot_modality_approach_category_sankey(df):
    df = _prepare_modality_approach_category(df)

    # --- Count flows ---
    counts = df.groupby(["Data Modality", "Approach group", "Category section"]).size().reset_index(name="count")

    modalities = list(df["Data Modality"].unique())
    approaches = list(df["Approach group"].unique())
    categories = list(df["Category section"].unique())

    labels = modalities + approaches + categories
    node_x = [0.01] * len(modalities) + [0.50] * len(approaches) + [0.99] * len(categories)

    # Node colors
    modality_colors = [FALLBACK_CATEGORY_COLOR] * len(modalities)
    approach_colors = [SECONDARY_PALETTE[i % len(SECONDARY_PALETTE)] for i in range(len(approaches))]
    category_colors = [FALLBACK_CATEGORY_COLOR] * len(categories)
    node_colors = modality_colors + approach_colors + category_colors

    # --- Map source/target indices ---
    source = []
    target = []
    value = []
    link_colors = []

    for _, row in counts.iterrows():
        approach_index = approaches.index(row["Approach group"])
        approach_color = approach_colors[approach_index]

        # Modality → Approach
        source.append(modalities.index(row["Data Modality"]))
        target.append(len(modalities) + approach_index)
        value.append(row["count"])
        link_colors.append(_hex_to_rgba(approach_color, LINK_ALPHA))

        # Approach → Category
        source.append(len(modalities) + approach_index)
        target.append(len(modalities) + len(approaches) + categories.index(row["Category section"]))
        value.append(row["count"] * MIDDLE_LINK_SCALE)
        link_colors.append(_hex_to_rgba(approach_color, LINK_ALPHA))

    # --- Build Sankey ---
    fig = go.Figure(go.Sankey(
        node=dict(
            label=labels,
            pad=15,
            thickness=15,
            color=node_colors,
            x=node_x,
            y=None,
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

    fig.write_image(OUTPUT_DIR / "modality_approach_category_sankey.pdf")


