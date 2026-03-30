import plotly.graph_objects as go

from const import OUTPUT_DIR, CATEGORY_COLORS, FALLBACK_CATEGORY_COLOR, SECONDARY_PALETTE


def plot_nodes_approach_category(df):
    """
    Create a regular node-link hierarchical diagram:
    Category -> Subcategory -> Approach.

    Subcategories and approaches are shared nodes (single node per label),
    so multiple parents can connect to the same node.
    """
    required_cols = ["Category (section)", "Subcategory (ai task)", "Approach group"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise KeyError(f"Missing required columns for node-link hierarchy plot: {missing_cols}")

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

    if cleaned.empty:
        raise ValueError("No valid rows available for node-link hierarchy plot after filtering.")

    cat_labels = sorted(cleaned["Category (section)"].unique().tolist())
    sub_labels = sorted(cleaned["Subcategory (ai task)"].unique().tolist())
    app_labels = sorted(cleaned["Approach group"].unique().tolist())

    cat_sub_edges = (
        cleaned
        .groupby(["Category (section)", "Subcategory (ai task)"])
        .size()
        .reset_index(name="count")
    )
    sub_app_edges = (
        cleaned
        .groupby(["Subcategory (ai task)", "Approach group"])
        .size()
        .reset_index(name="count")
    )

    cat_totals = cleaned.groupby("Category (section)").size().to_dict()
    sub_totals = cleaned.groupby("Subcategory (ai task)").size().to_dict()
    app_totals = cleaned.groupby("Approach group").size().to_dict()

    secondary_color_by_approach = {
        approach: SECONDARY_PALETTE[index % len(SECONDARY_PALETTE)]
        for index, approach in enumerate(app_labels)
    }

    def y_positions(labels):
        if len(labels) <= 1:
            return {labels[0]: 0.5} if labels else {}
        return {label: 1 - (idx / (len(labels) - 1)) for idx, label in enumerate(labels)}

    y_cat = y_positions(cat_labels)
    y_sub = y_positions(sub_labels)
    y_app = y_positions(app_labels)

    x_cat = 0.08
    x_sub = 0.50
    x_app = 0.92

    max_cat_sub = max(cat_sub_edges["count"].max(), 1)
    max_sub_app = max(sub_app_edges["count"].max(), 1)

    hierarchy_fig = go.Figure()
    link_count_annotations = []

    for _, row in cat_sub_edges.iterrows():
        cat = row["Category (section)"]
        sub = row["Subcategory (ai task)"]
        cnt = int(row["count"])
        width = 1 + (3 * cnt / max_cat_sub)
        mid_x = (x_cat + x_sub) / 2
        mid_y = (y_cat[cat] + y_sub[sub]) / 2
        hierarchy_fig.add_trace(
            go.Scatter(
                x=[x_cat, x_sub, None],
                y=[y_cat[cat], y_sub[sub], None],
                mode="lines",
                line=dict(color="rgba(120,120,120,0.40)", width=width),
                hoverinfo="text",
                text=[f"{cat} → {sub}<br>Count: {cnt}", "", ""],
                showlegend=False,
            )
        )
        link_count_annotations.append(
            dict(
                x=mid_x,
                y=mid_y,
                xref="x",
                yref="y",
                text=str(cnt),
                showarrow=False,
                font=dict(size=11, color="#222222"),
                bgcolor="rgba(255,255,255,0.70)",
                bordercolor="rgba(200,200,200,0.85)",
                borderwidth=0.5,
                xanchor="center",
                yanchor="middle",
            )
        )

    for _, row in sub_app_edges.iterrows():
        sub = row["Subcategory (ai task)"]
        app = row["Approach group"]
        cnt = int(row["count"])
        width = 1 + (3 * cnt / max_sub_app)
        mid_x = (x_sub + x_app) / 2
        mid_y = (y_sub[sub] + y_app[app]) / 2
        hierarchy_fig.add_trace(
            go.Scatter(
                x=[x_sub, x_app, None],
                y=[y_sub[sub], y_app[app], None],
                mode="lines",
                line=dict(color="rgba(120,120,120,0.40)", width=width),
                hoverinfo="text",
                text=[f"{sub} → {app}<br>Count: {cnt}", "", ""],
                showlegend=False,
            )
        )
        link_count_annotations.append(
            dict(
                x=mid_x,
                y=mid_y,
                xref="x",
                yref="y",
                text=str(cnt),
                showarrow=False,
                font=dict(size=11, color="#222222"),
                bgcolor="rgba(255,255,255,0.70)",
                bordercolor="rgba(200,200,200,0.85)",
                borderwidth=0.5,
                xanchor="center",
                yanchor="middle",
            )
        )

    max_cat = max(cat_totals.values()) if cat_totals else 1
    max_sub = max(sub_totals.values()) if sub_totals else 1
    max_app = max(app_totals.values()) if app_totals else 1

    cat_sizes = [16 + (24 * cat_totals[label] / max_cat) for label in cat_labels]
    sub_sizes = [14 + (20 * sub_totals[label] / max_sub) for label in sub_labels]
    app_sizes = [12 + (18 * app_totals[label] / max_app) for label in app_labels]

    hierarchy_fig.add_trace(
        go.Scatter(
            x=[x_cat] * len(cat_labels),
            y=[y_cat[label] for label in cat_labels],
            mode="markers+text",
            text=[f"{label} ({cat_totals[label]})" for label in cat_labels],
            textposition="top center",
            hovertemplate="<b>%{text}</b><extra></extra>",
            marker=dict(
                size=cat_sizes,
                color=[CATEGORY_COLORS.get(label, FALLBACK_CATEGORY_COLOR) for label in cat_labels],
                line=dict(width=1, color="#ffffff"),
            ),
            textfont=dict(size=14, color="#000000"),
            name="Category",
        )
    )

    hierarchy_fig.add_trace(
        go.Scatter(
            x=[x_sub] * len(sub_labels),
            y=[y_sub[label] for label in sub_labels],
            mode="markers+text",
            text=[f"{label} ({sub_totals[label]})" for label in sub_labels],
            textposition="top center",
            hovertemplate="<b>%{text}</b><extra></extra>",
            marker=dict(
                size=sub_sizes,
                color=[CATEGORY_COLORS.get(label, FALLBACK_CATEGORY_COLOR) for label in sub_labels],
                line=dict(width=1, color="#ffffff"),
            ),
            textfont=dict(size=13, color="#000000"),
            name="Subcategory",
        )
    )

    hierarchy_fig.add_trace(
        go.Scatter(
            x=[x_app] * len(app_labels),
            y=[y_app[label] for label in app_labels],
            mode="markers+text",
            text=[f"{label} ({app_totals[label]})" for label in app_labels],
            textposition="top center",
            hovertemplate="<b>%{text}</b><extra></extra>",
            marker=dict(
                size=app_sizes,
                color=[secondary_color_by_approach.get(label, FALLBACK_CATEGORY_COLOR) for label in app_labels],
                line=dict(width=1, color="#ffffff"),
            ),
            textfont=dict(size=13, color="#000000"),
            name="Approach",
        )
    )

    hierarchy_fig.update_layout(
        template="plotly_white",
        height=900,
        width=1400,
        margin=dict(l=30, r=30, t=60, b=30),
        title="Category → Subcategory → Approach (Node-link Diagram)",
        xaxis=dict(
            range=[0, 1],
            showgrid=False,
            zeroline=False,
            showticklabels=True,
            tickmode="array",
            tickvals=[x_cat, x_sub, x_app],
            ticktext=["Category", "Subcategory", "Approach"],
        ),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        annotations=link_count_annotations,
        showlegend=False,)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    hierarchy_fig.write_image(OUTPUT_DIR / "category_approach_node_link.pdf")
