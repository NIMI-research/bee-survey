
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import sequential
import math

from const import FALLBACK_CATEGORY_COLOR, INPUT_DIR, OUTPUT_DIR


def _inferno_colorscale_with_zero_fallback(max_count):
    inferno_palette = list(sequential.YlOrBr)

    if max_count <= 0:
        return [[0.0, FALLBACK_CATEGORY_COLOR], [1.0, FALLBACK_CATEGORY_COLOR]]

    # Keep fallback color only for exact 0 counts.
    # With integer counts and zmin=0, smallest positive value is 1/max_count in normalized scale.
    zero_band_end = 0.5 / float(max_count)
    scale = [[0.0, FALLBACK_CATEGORY_COLOR], [zero_band_end, FALLBACK_CATEGORY_COLOR]]

    for idx, color in enumerate(inferno_palette):
        position = zero_band_end + (1 - zero_band_end) * (idx / (len(inferno_palette) - 1))
        scale.append([position, color])

    return scale


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

    iso_reference = pd.read_csv(INPUT_DIR / "iso_codes.csv", usecols=["name", "alpha-3"], dtype=str).fillna("")
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
            colorscale=_inferno_colorscale_with_zero_fallback(max_count),
            zmin=0,
            zmax=zmax,
            colorbar=dict(
                title="Paper Count",
                tickmode="array",
                tickvals=tickvals,
                ticktext=[str(value) for value in tickvals],
            ),
        )
    )

    fig.update_layout(
        #where the bee comes from
        title="DEMOGRAPHIC FROM WHICH BEES ARE STUDIED",
        template="plotly_white",
        geo=dict(
            showframe=False,
            showcoastlines=True,
            showland=True,
            lataxis=dict(range=[-58, 90]),
            lonaxis=dict(range=[-180, 180]),
        ),
        height=700,
        width=1100,
    )

    fig.write_image(OUTPUT_DIR / "choropleth_country.pdf")
    fig.write_image(OUTPUT_DIR / "choropleth_country.png")