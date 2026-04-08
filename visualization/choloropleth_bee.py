import pandas as pd
import plotly.graph_objects as go
from plotly.colors import sequential
import math
import plotly.express as px
from const import FALLBACK_CATEGORY_COLOR, INPUT_DIR, OUTPUT_DIR
from utils import apply_legend_border, save_with_plot_border


def _stretched_colorscale(max_count, low_threshold=5, low_fraction=0.65):
    """
    Build a colorscale that dedicates `low_fraction` of the color spectrum
    to values in [0, low_threshold] and the remaining fraction to
    [low_threshold, max_count].

    Args:
        max_count:       Maximum count value in the data.
        low_threshold:   The value below which we want finer colour resolution (default 5).
        low_fraction:    Fraction of the colour spectrum assigned to [0, low_threshold] (default 0.65).
    """
    #spectral_palette = list(px.colors.diverging.Spectral_r)
    spectral_palette= [
    '#3288bd',  # Dark blue
    '#66c2a5',  # Teal
   '#abdda4',  # Light green
    '#e6f598',  # Pale yellow-green
    "#fed400",  # Light cream (center)
    '#fee090',  # Light yellow
    "#ee9943",  # Orange
    '#f46d43',  # Orange-red
    '#d53e4f',  # Dark red
]
    #inferno_palette = spectral_palette[2:] if len(spectral_palette) > 2 else spectral_palette
    #remove last 2 values
    inferno_palette = spectral_palette[:-2] if len(spectral_palette) > 2 else spectral_palette
    n = len(inferno_palette)
    fallback_color="rgba(128, 128, 128, 0.4)"  # dark gray with some transparency

    if max_count <= 0:
        return [[0.0, fallback_color], [1.0, fallback_color]]

    # Zero band: keep fallback colour for exact-zero cells
    zero_band_end = 0.5 / float(max_count)

    scale = [
        [0.0, fallback_color],
        [zero_band_end, fallback_color],
    ]

    # Clamp threshold so it sits strictly inside (0, max_count)
    threshold_norm = min(low_threshold / float(max_count), 0.95)

    # Split palette indices into two bands
    low_cutoff_idx = max(1, int(round(n * low_fraction)))  # palette index where low band ends
    low_cutoff_idx = min(low_cutoff_idx, n - 2)

    # --- Low band: zero_band_end → threshold_norm maps to palette[0..low_cutoff_idx] ---
    for i in range(low_cutoff_idx + 1):
        pos = zero_band_end + (threshold_norm - zero_band_end) * (i / low_cutoff_idx)
        scale.append([round(pos, 6), inferno_palette[i]])

    # --- High band: threshold_norm → 1.0 maps to palette[low_cutoff_idx..n-1] ---
    high_indices = list(range(low_cutoff_idx, n))
    for j, idx in enumerate(high_indices):
        pos = threshold_norm + (1.0 - threshold_norm) * (j / (len(high_indices) - 1))
        scale.append([round(pos, 6), inferno_palette[idx]])

    # Deduplicate consecutive identical positions (plotly requires strictly increasing)
    deduped = [scale[0]]
    for entry in scale[1:]:
        if entry[0] > deduped[-1][0]:
            deduped.append(entry)
        else:
            deduped[-1] = entry  # overwrite with latest colour at same position

    # Ensure it ends exactly at 1.0
    if deduped[-1][0] < 1.0:
        deduped.append([1.0, inferno_palette[-1]])

    return deduped


def plot_choropleth_country(df):
    df = df.copy()

    country_col = next(
        (
            col
            for col in ("bee_country", "Bee_country", "Country", "country")
            if col in df.columns
        ),
        None,
    )
    iso_col = next(
        (
            col
            for col in ("bee_iso", "Bee_iso", "Iso_code", "iso_code")
            if col in df.columns
        ),
        None,
    )
    if country_col is None or iso_col is None:
        raise ValueError("Missing required columns for choropleth: bee_country and bee_iso")

    df["_plot_country"] = df[country_col].fillna("").astype(str).str.strip()
    df["_plot_iso"] = df[iso_col].fillna("").astype(str).str.strip().str.upper()
    df = df[
        df["_plot_country"].ne("")
        & df["_plot_country"].ne("-")
        & df["_plot_iso"].ne("")
        & df["_plot_iso"].ne("-")
    ]
    df = df[
        df["_plot_iso"].ne("ATA")
        & df["_plot_country"].str.lower().ne("antarctica")
    ]

    if df.empty:
        return

    data = (
        df.groupby(["_plot_country", "_plot_iso"])
        .size()
        .reset_index(name="count")
        .rename(columns={"_plot_country": "Country", "_plot_iso": "iso_code"})
    )

    iso_reference = pd.read_csv(
        INPUT_DIR / "iso_codes.csv", usecols=["name", "alpha-3"], dtype=str
    ).fillna("")
    iso_reference = iso_reference.rename(columns={"name": "Country", "alpha-3": "iso_code"})
    iso_reference["iso_code"] = iso_reference["iso_code"].str.strip().str.upper()
    iso_reference = iso_reference[
        iso_reference["iso_code"].ne("")
        & iso_reference["iso_code"].ne("ATA")
        & iso_reference["Country"].str.strip().str.lower().ne("antarctica")
    ].drop_duplicates(subset=["iso_code"], keep="first")

    data = iso_reference.merge(data, on="iso_code", how="left", suffixes=("", "_obs"))
    data["Country"] = data["Country_obs"].fillna(data["Country"])
    data["count"] = data["count"].fillna(0)
    data = data[["Country", "iso_code", "count"]]

    max_count = float(data["count"].max()) if not data.empty else 0.0
    zmax = max(5, int(math.ceil(max_count / 5.0) * 5)) if max_count > 0 else 5
    tickvals = list(range(0, zmax + 1, 5))

    fig = go.Figure(
        data=go.Choropleth(
            locations=data["iso_code"],
            z=data["count"],
            text=data["Country"],
            colorscale=_stretched_colorscale(max_count, low_threshold=5, low_fraction=0.55),
            zmin=0,
            zmax=zmax,
            colorbar=dict(
                title=dict(text="Paper Count", font=dict(size=20, family="Arial Black")),
                len=0.75,
                tickmode="array",
                tickvals=tickvals,
                ticktext=[str(v) for v in tickvals],
                tickfont=dict(size=18, family="Arial Black"),
            ),
        )
    )

    fig.update_layout(
        title=dict(
            text="<b>Bee Demographics Represented in the Papers</b>",
            font=dict(size=40, family="Arial Black"),
            y=0.95,
        ),
        template="plotly_white",
        geo=dict(
            showframe=False,
            showcoastlines=True,
            coastlinecolor="#696969",
            projection=dict(type="natural earth", scale=1.08),
            # Explicit bounds prevent clipping and frame spacing issues
            lataxis=dict(range=[-60, 85]),
            lonaxis=dict(range=[-200, 200]),
        ),
        height=1000,
        width=1500,
        margin=dict(l=50, r=50, t=100, b=50),  # Control spacing around the plot
    )
    apply_legend_border(fig)
    save_with_plot_border(
        fig,
        png_path=OUTPUT_DIR / "choropleth_country.png",
        pdf_path=OUTPUT_DIR / "choropleth_country.pdf",
    )