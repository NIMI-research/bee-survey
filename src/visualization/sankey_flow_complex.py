import re
import plotly.graph_objects as go
from const import OUTPUT_DIR, CATEGORY_COLORS, FALLBACK_CATEGORY_COLOR, SECONDARY_PALETTE
import pandas as pd
from utils import apply_legend_border, save_with_plot_border

FALLBACK_CATEGORY_COLOR = "#585252"
MIDDLE_LINK_SCALE = 1.35
LINK_ALPHA = 0.22

# --- Modality bucketing config -------------------------------------------------
SINGLE_MODALITY = {
    "audio": "Audio",
    "video": "Video",
    "image": "Image",
    "images": "Image",
    "text": "Text",
    "tabular": "Tabular",
}
MULTIMODAL_WHITELIST = {
    frozenset({"audio", "image"}): "Multimodal (Audio, Image)",
    frozenset({"audio", "video"}): "Multimodal (Audio, Video)",
}
TIME_SERIES_ALIASES = ("time-series", "time series", "timeseries")


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


def _clean_token(s):
    """Strip stray 'Sensor Data:' prefixes and punctuation, title-case the result."""
    s = re.sub(r"^sensor\s*data\s*:?\s*", "", s.strip(), flags=re.IGNORECASE)
    return s.strip().strip(".,;:").title()


_GENERIC_FILLER_TOKENS = {"sensor", "data", "variables"}


def _extract_tokens(raw):
    """Pull the constituent data-type tokens out of a raw modality string,
    preferring whatever's in the last parenthetical group if present.
    Drops generic filler words (e.g. bare 'Sensor') that add no information
    once the token sits inside a bucket already named 'Sensor Signal'."""
    matches = re.findall(r'\(([^()]*)\)', raw)
    inner = matches[-1] if matches else raw
    inner = re.sub(r"^(multimodal|other|time[- ]?series)\s*", "", inner.strip(), flags=re.IGNORECASE)
    tokens = [t for t in (_clean_token(p) for p in re.split(r"[,/+]", inner)) if t]
    return [t for t in tokens if t.lower() not in _GENERIC_FILLER_TOKENS]


def extract_modality(val):
    """Classify a raw modality string into a bounded set of buckets.

    Returns (bucket, terms) where:
      - bucket is one of: Audio, Video, Image, Text, Tabular,
        Multimodal (Audio, Image), Multimodal (Audio, Video),
        Sensor Signal, Multimodal (Other), Other
      - terms is a comma-joined string of underlying data types (only
        populated for the catch-all buckets: Sensor Signal,
        Multimodal (Other), Other) used later to build a dynamic label.
    """
    raw = str(val).strip()
    if not raw:
        return "", ""

    raw_lower = re.sub(r"^sensor\s*data\s*:?\s*", "", raw.lower()).strip()
    base = _clean_token(re.split(r"[\(:]", raw_lower)[0]).lower()

    # Clean single modality: exactly one term, no separators.
    if base in SINGLE_MODALITY and not any(c in raw_lower for c in (",", "/", "+")):
        return SINGLE_MODALITY[base], ""

    tokens = _extract_tokens(raw)
    # Audio/Video/Image already have their own dedicated top-level nodes (or
    # whitelisted combo nodes) — they should never resurface inside a
    # catch-all bucket's bracket content, so strip them here once, up front,
    # rather than per-branch.
    non_core_tokens = [t for t in tokens if t.lower() not in ("audio", "video", "image")]

    is_time_series = any(alias in raw_lower for alias in TIME_SERIES_ALIASES)
    key = frozenset(t.lower() for t in tokens if t.lower() in ("audio", "image", "video"))
    if key == frozenset({"image", "video"}):
        key = frozenset()  # Image+Video is never a valid standalone combo

    if not is_time_series and key in MULTIMODAL_WHITELIST:
        return MULTIMODAL_WHITELIST[key], ""
    elif is_time_series:
        # Sensor Signal is for scalar/environmental readings only.
        return "Sensor Signal", ", ".join(non_core_tokens) if non_core_tokens else base.title()
    elif any(c in raw_lower for c in (",", "/", "+")) or base == "multimodal":
        return "Multimodal (Other)", ", ".join(non_core_tokens)
    else:
        return "Other", ", ".join(non_core_tokens) if non_core_tokens else base.title()


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

    # Classify each row into a bucket + underlying terms (for catch-all buckets).
    extracted = df[modality_col].fillna("").apply(extract_modality)
    df["Data Modality"] = extracted.map(lambda item: item[0])
    df["_modality_terms"] = extracted.map(lambda item: item[1])

    df["Approach group"] = df[approach_col].fillna("").astype(str).str.strip()
    df["Category section"] = df[category_col].apply(extract_category_section)

    invalid_rows = (
        is_empty_or_dash(df["Data Modality"])
        | is_empty_or_dash(df["Approach group"])
        | is_empty_or_dash(df["Category section"])
    )
    df = df[~invalid_rows].copy()

    # Build a dynamic, content-aware label for each catch-all bucket, e.g.
    # "Sensor Signal (Temperature, CO₂, Humidity…)" — aggregated across all #remove ...
    # rows that fell into that bucket, not just one row's phrasing.
    def _temperature_first_sort(terms):
        return sorted(terms, key=lambda t: (0 if t.lower() == "temperature" else 1, t.lower()))

    catch_all_buckets = ["Sensor Signal", "Multimodal (Other)", "Other"]
    bucket_terms = (
        df[df["Data Modality"].isin(catch_all_buckets)]
        .groupby("Data Modality")["_modality_terms"]
        .apply(lambda s: _temperature_first_sort({t for terms in s for t in terms.split(", ") if t}))
    )
    label_map = {}
    for bucket, terms in bucket_terms.items():
        preview = ", ".join(terms[:3]) #+ ("…" if len(terms) > 3 else "")
        label_map[bucket] = f"{bucket} ({preview})" if preview else bucket
    df["Data Modality"] = df["Data Modality"].replace(label_map)

    df = df.drop(columns=["_modality_terms"])
    return df


def _format_display_label(text):
    """Format labels for display: make plurals like 'Images' singular and render CO2 as CO₂.
    Operates on strings and returns a cleaned string for plotting labels.
    """
    if pd.isna(text):
        return ""
    s = str(text)
    # Normalize common plural 'Images' -> 'Image'
    s = re.sub(r'\bImages\b', 'Image', s, flags=re.IGNORECASE)
    s = re.sub(r'\bimages\b', 'Image', s, flags=re.IGNORECASE)
    # Replace CO2 variants with proper subscript 2
    s = re.sub(r'\bco2\b', 'CO₂', s, flags=re.IGNORECASE)
    s = re.sub(r'\bco₂\b', 'CO₂', s, flags=re.IGNORECASE)
    return s


def plot_modality_approach_category_sankey(df):
    df = _prepare_modality_approach_category(df)
    df = df[~df["Data Modality"].str.startswith("Multimodal (Other)", na=False)].copy()

    # --- Count flows ---
    counts = df.groupby(["Data Modality", "Approach group", "Category section"]).size().reset_index(name="count")

    modality_totals = counts.groupby("Data Modality", as_index=False)["count"].sum()
    approach_totals = counts.groupby("Approach group", as_index=False)["count"].sum()
    category_totals = counts.groupby("Category section", as_index=False)["count"].sum()

    modality_totals = modality_totals.sort_values(["count"], ascending=[False])
    approach_totals = approach_totals.sort_values(["Approach group"], ascending=[True])
    category_totals = category_totals.sort_values(["count"], ascending=[False])

    modalities = modality_totals["Data Modality"].tolist()
    approaches = approach_totals["Approach group"].tolist()
    categories = category_totals["Category section"].tolist()

    labels = modalities + approaches + categories
    display_labels = [_format_display_label(label) for label in labels]
    bold_labels = [f"<b>{label}</b>" for label in display_labels]
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
        textfont=dict(family="Arial", size=17),
        node=dict(
            label=bold_labels,
            pad=35,
            thickness=18,
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
        title=dict(
            text="<b>Flow from Data Modality to Approach and Category</b>",
            font=dict(family="Arial", size=24),
        ),
        font=dict(family="Arial"),
        height=700,
        width=1400
    )
    apply_legend_border(fig)
    save_with_plot_border(
        fig,
        png_path=OUTPUT_DIR / "modality_approach_category_sankey.png",
        pdf_path=OUTPUT_DIR / "modality_approach_category_sankey_v2.pdf",
    )