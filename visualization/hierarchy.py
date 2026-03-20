import plotly.graph_objects as go
import math
from const import OUTPUT_DIR, CATEGORY_COLORS, FALLBACK_CATEGORY_COLOR, SECONDARY_PALETTE


MIN_FONT_SIZE = 12
TEXT_TEMPLATE = "%{text}"

def plot_category_approach_hierarchy(df):
    """
    Creates a Tree (Treemap) visualization for Category → Subcategory → Approach hierarchy.
    Aggregates counts to avoid duplicate labels.
    """

    required_cols = ["Category (section)", "Subcategory (ai task)", "Approach group"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise KeyError(f"Missing required columns for hierarchy plot: {missing_cols}")

    # Clean invalid rows (empty or dash-only)
    cleaned = df.copy()

    def normalize_category_text(value):
        text = str(value).strip()
        if "—" in text:
            return text.split("—", 1)[0].strip()
        return " ".join(text.split()[:5])

    cleaned[required_cols] = cleaned[required_cols].fillna("").astype(str)
    for col in required_cols:
        cleaned[col] = cleaned[col].str.strip()

    cleaned["Category (section)"] = cleaned["Category (section)"].map(normalize_category_text)

    invalid = (
        cleaned["Category (section)"].eq("")
        | cleaned["Subcategory (ai task)"].eq("")
        | cleaned["Approach group"].eq("")
        | cleaned["Category (section)"].str.fullmatch(r"-+", na=False)
        | cleaned["Subcategory (ai task)"].str.fullmatch(r"-+", na=False)
        | cleaned["Approach group"].str.fullmatch(r"-+", na=False)
    )
    cleaned = cleaned[~invalid].copy()

    # Aggregate counts
    df_counts = (
        cleaned
        .groupby(["Category (section)", "Subcategory (ai task)", "Approach group"])
        .size()
        .reset_index(name="count")
    )

    if df_counts.empty:
        raise ValueError("No valid rows available for hierarchy plot after filtering.")

    unique_approaches = list(df_counts["Approach group"].unique())
    secondary_color_by_approach = {
        approach: SECONDARY_PALETTE[index % len(SECONDARY_PALETTE)]
        for index, approach in enumerate(unique_approaches)
    }

    # Build hierarchy lists
    ids = []
    labels = []
    parents = []
    values = []
    colors = []
    texts = []
    text_templates = []
    node_types = []

    # Keep track of added nodes
    added_nodes = set()

    def add_node(node_id, label, parent_id, value, color, text_value, node_type, allow_duplicates=False):
        if not allow_duplicates and node_id in added_nodes:
            return
        ids.append(node_id)
        labels.append(label)
        parents.append(parent_id)
        values.append(value)
        colors.append(color)
        texts.append(text_value)
        text_templates.append(TEXT_TEMPLATE)
        node_types.append(node_type)
        added_nodes.add(node_id)

    for _, row in df_counts.iterrows():
        cat = row["Category (section)"]
        sub = row["Subcategory (ai task)"]
        app = row["Approach group"]
        val = row["count"]

        cat_id = f"cat::{cat}"
        sub_id = f"sub::{cat}::{sub}"
        app_id = f"app::{cat}::{sub}::{app}"

        # Category node
        add_node(
            node_id=cat_id,
            label=cat,
            parent_id="",
            value=0,  # Plotly ignores value for non-leaf nodes
            color=FALLBACK_CATEGORY_COLOR,
            text_value=cat,
            node_type="category",
        )

        # Subcategory node
        add_node(
            node_id=sub_id,
            label=sub,
            parent_id=cat_id,
            value=0,
            color=CATEGORY_COLORS.get(sub, CATEGORY_COLORS.get(cat, FALLBACK_CATEGORY_COLOR)),
            text_value=sub,
            node_type="subcategory",
        )

        # Approach node
        add_node(
            node_id=app_id,
            label="",
            parent_id=sub_id,
            value=val,
            color=secondary_color_by_approach.get(app, FALLBACK_CATEGORY_COLOR),
            text_value=str(int(val)),
            node_type="approach",
            allow_duplicates=True,
        )

    legend_items = list(secondary_color_by_approach.items())
    legend_shapes = []
    legend_annotations = []
    if legend_items:
        start_x = 0.01
        end_x = 0.99
        row_ys = [-0.10, -0.15]
        items_per_row = math.ceil(len(legend_items) / 3)
        item_width = (end_x - start_x) / max(items_per_row, 1)

        for index, (approach_name, approach_color) in enumerate(legend_items):
            row = index // items_per_row
            col = index % items_per_row
            if row > 1:
                break

            item_start = start_x + col * item_width
            y_center = row_ys[row]
            line_start = item_start + (item_width * 0.02)
            line_end = item_start + min(item_width * 0.42, 0.16)
            legend_shapes.append(
                dict(
                    type="line",
                    xref="paper",
                    yref="paper",
                    x0=line_start,
                    x1=line_end,
                    y0=y_center,
                    y1=y_center,
                    line=dict(width=4, color=approach_color),
                )
            )
            legend_annotations.append(
                dict(
                    x=line_end + 0.004,
                    y=y_center,
                    xref="paper",
                    yref="paper",
                    text=approach_name,
                    showarrow=False,
                    xanchor="left",
                    yanchor="middle",
                    align="left",
                    font=dict(size=9, color="#333333"),
                )
            )

    # --- TREE (Treemap) ---
    tree_fig = go.Figure(go.Treemap(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        text=texts,
        textinfo="text",
        texttemplate=text_templates,
        branchvalues="remainder",
        customdata=node_types,
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Count: %{value}<br>"
            "Type: %{customdata}<extra></extra>"
        ),
        marker=dict(colors=colors),
        textfont=dict(size=MIN_FONT_SIZE)
    ))
    tree_fig.update_layout(
        template="plotly_white",
        height=500,
        width=800,
        margin=dict(l=20, r=20, t=60, b=170),
        shapes=legend_shapes,
        annotations=legend_annotations,
        uniformtext=dict(minsize=MIN_FONT_SIZE),
        title="Category → Subcategory → Approach (Tree)"
    )
    tree_fig.write_image(OUTPUT_DIR / "category_approach_tree.pdf")
