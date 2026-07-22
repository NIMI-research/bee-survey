import os
import pandas as pd
import plotly.graph_objects as go
from const import SECONDARY_PALETTE, OUTPUT_DIR, SECONDARY_PALETTE
from utils import apply_legend_border, save_with_plot_border


def _clip_approach_text(text, max_words=5):
    """Clip approach text at em dash or limit to max_words."""
    if not text:
        return text
    if "—" in text:
        text = text.split("—")[0].strip()
    words = text.split()
    if len(words) > max_words:
        text = " ".join(words[:max_words])
    return text
def ridge_plot_approaches_over_years(df):
    try:
        if df is None or df.empty:
            print("[ridge_plot_approaches_over_years] ERROR: input dataframe is None or empty.")
            return

        df = df.copy()

        required_cols = {"Approach group", "Year"}
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            print(f"[ridge_plot_approaches_over_years] ERROR: missing required columns: {missing_cols}")
            return

        df = df.dropna(subset=["Approach group"])
        df["Approach group"] = df["Approach group"].astype(str).str.strip()
        df = df[df["Approach group"] != ""]
        df["Approach group"] = df["Approach group"].map(lambda x: _clip_approach_text(x))

        df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
        n_before = len(df)
        df = df.dropna(subset=["Year"])
        n_dropped = n_before - len(df)
        if n_dropped > 0:
            print(f"[ridge_plot_approaches_over_years] WARNING: dropped {n_dropped} row(s) with invalid/missing Year.")
        df["Year"] = df["Year"].astype(int)

        if df.empty:
            print("[ridge_plot_approaches_over_years] ERROR: dataframe empty after cleaning Approach group / Year.")
            return

        data = df.groupby(["Approach group", "Year"]).size().reset_index(name="count")
        years = sorted(data["Year"].unique())

        approach_order = (
            data.groupby("Approach group", as_index=False)
            .agg(latest_year=("Year", "max"))
            .sort_values(["latest_year", "Approach group"], ascending=[False, True])
        )
        approaches = approach_order["Approach group"].tolist()

        n_approaches = len(approaches)
        if n_approaches == 0:
            print("[ridge_plot_approaches_over_years] ERROR: no approach groups found after cleaning.")
            return

        spacing = 1.6          # increased from 1.0 — more vertical room between ridges
        ridge_fill_frac = 0.65  # increased from implicit 0.85->now smaller fraction of spacing so ridge peak sits lower within its own band, leaving a buffer before the next ridge starts

        fig = go.Figure()

        for idx, approach in enumerate(approaches):
            cat_data = (
                data[data["Approach group"] == approach]
                .set_index("Year")["count"]
                .reindex(years, fill_value=0)
            )

            y_offset = idx * spacing
            color = SECONDARY_PALETTE[idx % len(SECONDARY_PALETTE)]

            y_values = cat_data.values.astype(float)
            y_max_val = y_values.max() if y_values.max() > 0 else 1
            y_scaled = y_values / y_max_val * (spacing * ridge_fill_frac)

            fig.add_trace(
                go.Scatter(
                    x=list(years) + list(years)[::-1],
                    y=list(y_scaled + y_offset) + [y_offset] * len(years),
                    fill="toself",
                    fillcolor=color,
                    line=dict(color=color, width=1.5, shape="spline", smoothing=0.75),
                    opacity=0.6,
                    name=approach,
                    showlegend=True,
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=[years[0]], y=[0],
                    yaxis="y2",
                    mode="markers",
                    marker=dict(opacity=0),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

            fig.add_trace(
                go.Scatter(
                    x=years,
                    y=list(y_scaled + y_offset),
                    mode="lines",
                    line=dict(color=color, width=2),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

        # --- Vertical axis scale: per-ridge tick marks + peak value annotation ---
        shapes = []
        annotations = []
        for idx, approach in enumerate(approaches):
            cat_data = (
                data[data["Approach group"] == approach]
                .set_index("Year")["count"]
                .reindex(years, fill_value=0)
            )
            y_offset = idx * spacing
            peak_count = int(cat_data.values.max())

            annotations.append(
                dict(
                    x=years[0] - 0.4, y=y_offset,
                    xref="x", yref="y",
                    text="0",
                    showarrow=False,
                    font=dict(size=12, family="Arial Black", color="#696969"),
                    xanchor="right",
                )
            )
            annotations.append(
                dict(
                    x=years[0] - 0.4, y=y_offset + spacing * ridge_fill_frac,
                    xref="x", yref="y",
                    text=str(peak_count),
                    showarrow=False,
                    font=dict(size=12, family="Arial Black", color="#696969"),
                    xanchor="right",
                )
            )
            shapes.append(
                dict(
                    type="line",
                    xref="x", yref="y",
                    x0=years[0] - 0.35, x1=years[0] - 0.35,
                    y0=y_offset, y1=y_offset + spacing * ridge_fill_frac,
                    line=dict(color="#696969", width=1.3),
                )
            )

        fig.update_layout(
            template="plotly_white",
            paper_bgcolor="white",
            plot_bgcolor="white",
            height=250 + n_approaches * 90,
            width=1500,
            shapes=shapes,
            annotations=annotations,
            xaxis=dict(
                title=dict(
                    text="(density scaled independently per approach group)</span>",
                    font=dict(size=18, family="Arial"),
                ),
                showgrid=False,
                tickfont=dict(size=18, family="Arial Black"),
                tickmode="array",
                tickvals=years,
                ticktext=[str(y) for y in years],
                range=[years[0] - 1.3, years[-1] + 0.5],
            ),
            yaxis=dict(
                autorange="min",
                tickmode="array",
                tickvals=[i * spacing + spacing * (ridge_fill_frac / 2) for i in range(n_approaches)],
                ticktext=approaches,
                showgrid=False,
                ticklabelstandoff=18,
                tickfont=dict(size=20),
            ),
            yaxis2=dict(
                overlaying="y",
                side="right",
                showticklabels=False,
                showgrid=False,
                title=dict(
                    text="Annual Number of Studies",
                    font=dict(size=30, family="Arial"),
                ),
            ),
            showlegend=False,
            margin=dict(t=10, b=80, l=260, r=90),  # bumped r to make room for the label
            xaxis_showline=True,
            xaxis_linewidth=2,
            xaxis_linecolor="black",
            yaxis_showline=False,
        )
        apply_legend_border(fig)

        png_path = OUTPUT_DIR / "ridge_approaches_over_years.png"
        pdf_path = OUTPUT_DIR / "ridge_approaches_over_years_amp.pdf"

        save_with_plot_border(fig, png_path=png_path, pdf_path=pdf_path)

        for path in (png_path, pdf_path):
            if os.path.exists(path):
                print(f"[ridge_plot_approaches_over_years] SUCCESS: saved {path} (exists, {os.path.getsize(path)} bytes)")
            else:
                print(f"[ridge_plot_approaches_over_years] ERROR: expected output not found at {path}")

    except Exception as e:
        print(f"[ridge_plot_approaches_over_years] ERROR: exception during plot generation: {e}")
        raise