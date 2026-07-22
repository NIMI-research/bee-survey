import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go

from const import OUTPUT_DIR, SOURCE_WORKBOOK_PATH
from utils import apply_legend_border, save_with_plot_border

# ---------------------------------------------------------------------------
# Helpers – geometry
# ---------------------------------------------------------------------------

PI = np.pi

COLOR_PALETTE = list(px.colors.sequential.Brwnyl) + list(px.colors.sequential.YlOrBr)
MIN_MIGRATION_GEOMETRY_WEIGHT = 5.0


def _load_country_region_metadata():
    try:
        iso_df = pd.read_excel(
            SOURCE_WORKBOOK_PATH,
            sheet_name="iso_codes",
            usecols=["name", "region", "region-code"],
            dtype=str,
        ).fillna("")
    except Exception:
        return {}, {}

    iso_df["name"] = iso_df["name"].astype(str).str.strip()
    iso_df["region"] = iso_df["region"].astype(str).str.strip()
    iso_df["region-code"] = iso_df["region-code"].astype(str).str.strip()

    country_to_region = {
        row["name"]: row["region"]
        for _, row in iso_df.iterrows()
        if row["name"]
    }

    region_to_code = {}
    for _, row in iso_df.iterrows():
        region = row["region"]
        code = row["region-code"]
        if not region or region in region_to_code:
            continue
        region_to_code[region] = int(code) if str(code).isdigit() else 10**9

    return country_to_region, region_to_code


def _country_region_sort_order(countries, country_to_region, region_to_code):
    countries = list(countries)
    if not countries:
        return []

    if not country_to_region:
        return sorted(countries)

    unknown_region_rank = 10**9

    return sorted(
        countries,
        key=lambda country: (
            region_to_code.get(country_to_region.get(country, ""), unknown_region_rank),
            country_to_region.get(country, "ZZZ"),
            country,
        ),
    )


def _build_continent_arc_traces(countries, country_to_region, region_to_code, ideo_ends, radius):
    if not countries:
        return []

    segments = []
    start_idx = 0
    while start_idx < len(countries):
        region = country_to_region.get(countries[start_idx], "").strip()
        end_idx = start_idx
        while (
            end_idx + 1 < len(countries)
            and country_to_region.get(countries[end_idx + 1], "").strip() == region
        ):
            end_idx += 1

        if region and end_idx > start_idx:
            segments.append((region, start_idx, end_idx))
        start_idx = end_idx + 1

    if not segments:
        return []

    unique_regions = sorted(
        {region for region, _, _ in segments},
        key=lambda region: (region_to_code.get(region, 10**9), region),
    )
    region_colors = {
        region: _hex_to_rgba(COLOR_PALETTE[i % len(COLOR_PALETTE)], 0.95)
        for i, region in enumerate(unique_regions)
    }

    traces = []
    for region, left, right in segments:
        z_arc = _make_ideogram_arc(radius, (ideo_ends[left][0], ideo_ends[right][1]), n_pts=90)
        traces.append(go.Scatter(
            x=z_arc.real,
            y=z_arc.imag,
            mode="lines",
            line=dict(color=region_colors[region], width=8),
            text=f"{region}<br>Countries: {right - left + 1}",
            hoverinfo="text",
            showlegend=False,
        ))

    return traces


def _hex_to_rgba(hex_color: str, alpha: float = 0.75) -> str:
    color = str(hex_color).strip()
    if color.lower().startswith("rgba("):
        inner = color[color.find("(") + 1: color.rfind(")")]
        parts = [p.strip() for p in inner.split(",")]
        if len(parts) >= 3:
            return f"rgba({parts[0]},{parts[1]},{parts[2]},{alpha})"
    if color.lower().startswith("rgb("):
        inner = color[color.find("(") + 1: color.rfind(")")]
        parts = [p.strip() for p in inner.split(",")]
        if len(parts) >= 3:
            return f"rgba({parts[0]},{parts[1]},{parts[2]},{alpha})"

    h = color.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    if len(h) != 6:
        return f"rgba(127,127,127,{alpha})"

    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return f"rgba(127,127,127,{alpha})"
    return f"rgba({r},{g},{b},{alpha})"


def _moduloAB(x, a, b):
    if a >= b:
        raise ValueError("Incorrect interval ends")
    y = (x - a) % (b - a)
    return y + b if y < 0 else y + a


def _test_2PI(x):
    return 0 <= x < 2 * PI


def _ideogram_ends(ideogram_len, gap):
    ends, left = [], 0
    for length in ideogram_len:
        ends.append((left, left + length))
        left += length + gap
    return ends


def _make_ideogram_arc(R, phi, n_pts=50):
    """Return complex array of points along arc at radius R between angles phi[0]..phi[1]."""
    phi = [_moduloAB(t, 0, 2 * PI) for t in phi]
    if phi[0] < phi[1]:
        theta = np.linspace(phi[0], phi[1], n_pts)
    else:
        phi = [_moduloAB(t, -PI, PI) for t in phi]
        theta = np.linspace(phi[0], phi[1], n_pts)
    return R * np.exp(1j * theta)


def _map_data(matrix, row_sum, ideogram_length):
    n = matrix.shape[0]
    mapped = np.zeros((n, n))
    for j in range(n):
        mapped[:, j] = np.where(row_sum > 0, ideogram_length * matrix[:, j] / row_sum, 0)

    return mapped


def _ribbon_ends(mapped_data, ideo_ends, idx_sort):
    n = mapped_data.shape[0]
    boundary = np.zeros((n, n + 1))
    for k in range(n):
        start = ideo_ends[k][0]
        boundary[k][0] = start
        for j in range(1, n + 1):
            J = idx_sort[k][j - 1]
            boundary[k][j] = start + mapped_data[k][J]
            start = boundary[k][j]
    return [[(boundary[k][j], boundary[k][j + 1]) for j in range(n)] for k in range(n)]


def _control_pts(angle, radius):
    b = np.array([np.exp(1j * a) for a in angle], dtype=complex)
    b[1] *= radius
    return list(zip(b.real, b.imag))


def _ctrl_rib_chords(l, r, radius=0.2):
    return [_control_pts([l[j], (l[j] + r[j]) / 2, r[j]], radius) for j in range(2)]


def _make_q_bezier(b):
    A, B, C = b
    return f"M {A[0]},{A[1]} Q {B[0]},{B[1]} {C[0]},{C[1]}"


def _make_ribbon_arc(theta0, theta1, n_pts=40):
    # Normalize into [0, 2PI) unconditionally

    theta0 = _moduloAB(theta0, 0, 2 * PI)
    theta1 = _moduloAB(theta1, 0, 2 * PI)
    diff = abs(theta0 - theta1)
    nr = 3 if np.isnan(diff) else max(3, int(40 * diff / PI))
    if theta0 < theta1:
        theta0 = _moduloAB(theta0, -PI, PI)
        theta1 = _moduloAB(theta1, -PI, PI)
    nr = max(3, int(40 * abs(theta0 - theta1) / PI))
    theta = np.linspace(theta0, theta1, nr)
    pts = np.exp(1j * theta)
    return " ".join(f"L {p.real},{p.imag}" for p in pts)


def _make_ribbon_shape(l, r, line_color, fill_color, radius=0.2):
    poly = _ctrl_rib_chords(l, r, radius)
    b, c = poly
    path = (
        _make_q_bezier(b)
        + " " + _make_ribbon_arc(r[0], r[1])
        + " " + _make_q_bezier(c[::-1])
        + " " + _make_ribbon_arc(l[1], l[0])
    )
    return dict(
        type="path",
        path=path,
        fillcolor=fill_color,
        line=dict(color=line_color, width=0.5),
        layer="below",
    )


def _make_self_rel_shape(l, line_color, fill_color, radius=0.2):
    b = _control_pts([l[0], (l[0] + l[1]) / 2, l[1]], radius)
    path = _make_q_bezier(b) + " " + _make_ribbon_arc(l[1], l[0])
    return dict(
        type="path",
        path=path,
        fillcolor=fill_color,
        line=dict(color=line_color, width=0.5),
        layer="below",
    )


def _make_ideo_shape(path, line_color, fill_color):
    return dict(
        type="path",
        path=path,
        fillcolor=fill_color,
        line=dict(color=line_color, width=0.45),
        layer="below",
    )


def _invPerm(perm):
    inv = [0] * len(perm)
    for i, s in enumerate(perm):
        inv[s] = i
    return inv


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------
def plot_circular_migration_bee_research(df):
    df = df.copy()
    country_to_region, region_to_code = _load_country_region_metadata()

    df = df.rename(columns={
        "Bee_country": "Bee Country",
        "Research_country": "Research Country",
    })
    for col in ("Bee Country", "Research Country"):
        df[col] = df[col].fillna("").astype(str).str.strip()
    df = df[(df["Bee Country"] != "") & (df["Research Country"] != "")]
    if df.empty:
        return

    flows = (
        df.groupby(["Bee Country", "Research Country"])
        .size()
        .reset_index(name="count")
    )
    countries = _country_region_sort_order(
        pd.unique(flows[["Bee Country", "Research Country"]].values.ravel()),
        country_to_region,
        region_to_code,
    )
    n = len(countries)
    idx = {c: i for i, c in enumerate(countries)}

    matrix = np.zeros((n, n), dtype=float)
    for _, row in flows.iterrows():
        matrix[idx[row["Bee Country"]], idx[row["Research Country"]]] += row["count"]

    total_flow = matrix.sum(axis=1) + matrix.sum(axis=0)
    keep_idx = np.where(total_flow > 0)[0]
    if len(keep_idx) == 0:
        return
    countries = [countries[i] for i in keep_idx]
    matrix = matrix[np.ix_(keep_idx, keep_idx)]
    n = len(countries)

    ideo_colors = [_hex_to_rgba(COLOR_PALETTE[i % len(COLOR_PALETTE)], 0.75) for i in range(n)]

    # ── Fix ribbon widths: use symmetric matrix so both sides of a ribbon
    #    are sized by max(forward, backward) flow, never collapsing to 0 ──
    sym_matrix = np.maximum(matrix, matrix.T)   # each cell = max of both directions

    # Ensure a visible minimum ribbon thickness for any non-zero migration flow.
    # This affects only geometry; hover text still reports raw counts from matrix.
    geom_matrix = sym_matrix.copy()
    non_zero = geom_matrix > 0
    geom_matrix[non_zero] = np.maximum(
        geom_matrix[non_zero],
        MIN_MIGRATION_GEOMETRY_WEIGHT,
    )

    row_sum    = geom_matrix.sum(axis=1)          # drives arc length AND ribbon width

    gap = 2 * PI * 0.005
    ideogram_length = 2 * PI * row_sum / row_sum.sum() - gap * np.ones(n)
    ideogram_length = np.maximum(ideogram_length, 1e-4)
    ideo_ends = _ideogram_ends(ideogram_length, gap)

    mapped_data = _map_data(geom_matrix, row_sum, ideogram_length)
    idx_sort    = np.argsort(mapped_data, axis=1)
    ribbon_ends = _ribbon_ends(mapped_data, ideo_ends, idx_sort)
    ribbon_color = [[ideo_colors[k]] * n for k in range(n)]

    shapes      = []
    ribbon_info = []

    for k in range(n):
        sigma_inv = _invPerm(idx_sort[k])
        for j in range(k, n):
            if matrix[k, j] == 0 and matrix[j, k] == 0:
                continue
            l = ribbon_ends[k][sigma_inv[j]]
            if j == k:
                shapes.append(
                    _make_self_rel_shape(l, "rgb(175,175,175)", ideo_colors[k], radius=0.2)
                )
                z = 0.9 * np.exp(1j * (l[0] + l[1]) / 2)
                ribbon_info.append(go.Scatter(
                    x=[z.real], y=[z.imag], mode="markers",
                    text=f"{countries[k]} → {countries[k]}<br>Count: {int(matrix[k,k])}",
                    hoverinfo="text",
                    marker=dict(size=0.5, color=ideo_colors[k]),
                    showlegend=False,
                ))
            else:
                eta_inv = _invPerm(idx_sort[j])
                r = ribbon_ends[j][eta_inv[k]]
                zi = 0.9 * np.exp(1j * (l[0] + l[1]) / 2)
                zf = 0.9 * np.exp(1j * (r[0] + r[1]) / 2)
                total_flow_kj = matrix[k, j] + matrix[j, k]
                if matrix[k, j] > 0:
                    ribbon_info.append(go.Scatter(
                        x=[zi.real], y=[zi.imag], mode="markers",
                        text=f"{countries[k]} → {countries[j]}<br>Count: {int(matrix[k,j])}<br>Total both ways: {int(total_flow_kj)}",
                        hoverinfo="text",
                        marker=dict(size=0.5, color=ribbon_color[k][j]),
                        showlegend=False,
                    ))
                if matrix[j, k] > 0:
                    ribbon_info.append(go.Scatter(
                        x=[zf.real], y=[zf.imag], mode="markers",
                        text=f"{countries[j]} → {countries[k]}<br>Count: {int(matrix[j,k])}<br>Total both ways: {int(total_flow_kj)}",
                        hoverinfo="text",
                        marker=dict(size=0.5, color=ribbon_color[j][k]),
                        showlegend=False,
                    ))
                dominant = ribbon_color[k][j] if matrix[k, j] >= matrix[j, k] else ribbon_color[j][k]
                shapes.append(
                    _make_ribbon_shape(l, (r[1], r[0]), "rgb(175,175,175)", dominant, radius=0.2)
                )

    # Draw ideogram arcs
    ideograms = []
    R_outer, R_inner = 1.26, 1.15
    continent_arc_traces = _build_continent_arc_traces(
        countries,
        country_to_region,
        region_to_code,
        ideo_ends,
        radius=R_outer + 0.09,
    )

    for k in range(n):
        z_out = _make_ideogram_arc(R_outer, ideo_ends[k])
        z_in  = _make_ideogram_arc(R_inner, ideo_ends[k])

        ideograms.append(go.Scatter(
            x=z_out.real, y=z_out.imag, mode="lines",
            line=dict(color=ideo_colors[k], width=0.25, shape="spline"),
            text=f"{countries[k]}<br>Total: {int(row_sum[k])}",
            hoverinfo="text",
            showlegend=False,
        ))

        m = len(z_out)
        path = "M " + " L ".join(f"{z_out.real[s]},{z_out.imag[s]}" for s in range(m))
        zi_rev = z_in[::-1]
        path += " L " + " L ".join(f"{zi_rev.real[s]},{zi_rev.imag[s]}" for s in range(m))
        path += f" L {z_out.real[0]},{z_out.imag[0]}"
        shapes.append(_make_ideo_shape(path, "rgb(150,150,150)", ideo_colors[k]))

    # ── Fix labels: cascade radius tiers with full wrap-around handling ───
    R_BASE    = R_outer + 0.22
    R_STEP    = 0.15
    MIN_GAP   = np.deg2rad(6)   # minimum angular separation

    label_specs = []
    for k in range(n):
        mid = (ideo_ends[k][0] + ideo_ends[k][1]) / 2
        label_specs.append({"k": k, "angle": mid % (2 * PI)})
    label_specs.sort(key=lambda s: s["angle"])

    # Cascade: keep bumping radius until clear of ALL previously placed labels
    placed = []  # list of (angle, radius)
    for spec in label_specs:
        angle = spec["angle"]
        r = R_BASE
        changed = True
        while changed:
            changed = False
            for pa, pr in placed:
                raw_gap = abs(angle - pa)
                gap = min(raw_gap, 2 * PI - raw_gap)   # true shortest arc
                # scale angular tolerance by radius (outer labels need less gap)
                needed = MIN_GAP * (R_BASE / r)
                if gap < needed and abs(r - pr) < R_STEP * 0.8:
                    r += R_STEP
                    changed = True
                    break
        placed.append((angle, r))
        spec["r"] = r

    annotations = []
    for spec in label_specs:
        k     = spec["k"]
        angle = spec["angle"]
        r     = spec["r"]
        if "united states" in countries[k].lower() or "germany" in countries[k].lower():
            r += 0.1
        deg   = np.degrees(angle)

        lx = r * np.cos(angle)
        ly = r * np.sin(angle)

        if 90 < deg % 360 < 270:
            textangle = (deg + 180) % 360
            xanchor   = "right"
        else:
            textangle = deg % 360
            xanchor   = "left"

        country_label = countries[k]
        if " and " in country_label.lower() or "," in country_label.lower():
            country_label = country_label.split("and", 1)[0].strip()
            country_label = country_label.split(",", 1)[0].strip()

        annotations.append(dict(
            x=lx, y=ly,
            text=country_label,
            showarrow=False,
            font=dict(size=14, color="#333"),
            xanchor=xanchor,
            yanchor="middle",
            textangle=-textangle,
            xref="x", yref="y",
        ))

    data = continent_arc_traces + ideograms + ribbon_info

    axis_cfg = dict(
        showline=False, zeroline=False, showgrid=False,
        showticklabels=False, title="",
    )
    layout = dict(
        title="Circular Migration: Bee Demographic → Research Demographic",
        font=dict(size=13),
        xaxis={**axis_cfg, "range": [-2.0, 2.0]},
        yaxis={**axis_cfg, "range": [-2.0, 2.0], "scaleanchor": "x"},
        showlegend=False,
        hovermode="closest",
        margin=dict(t=60, b=40, l=40, r=40),
        height=950,
        width=950,
        shapes=shapes,
        annotations=annotations,
        template="plotly_white",
    )

    fig = go.Figure(data=data, layout=layout)
    apply_legend_border(fig)
    save_with_plot_border(
        fig,
        png_path=OUTPUT_DIR / "circular_migration_bee_research.png",
        pdf_path=OUTPUT_DIR / "circular_migration_bee_research.pdf",
        scale=2,
    )