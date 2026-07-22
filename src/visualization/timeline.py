import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, RegularPolygon
import numpy as np
import pandas as pd
import re

from const import OUTPUT_DIR
from utils import save_with_plot_border


PALETTE = [
    "#FFF9E6",
    "#F0F0F0",
    "#FFE6F0",
    "#E6F9F0",
    "#E6F1FB",
    "#F3E6FB",
    "#FDECC8",
    "#E8F8F0",
    "#FBE9E7",
    "#EDE7F6",
]

TRUNCATE_GROUPS = {
    "object detection / segmentation",
    "cnn & variants",
    "domain specific / specialized",
}

TIMELINE_SIZE_PX = (1200, 700)
TIMELINE_EXPORT_DPI = 380

class RoadmapGenerator:
    def __init__(self, start_year=2011, end_year=2025, size_px=(1500, 900), years=None, dpi=100, pivot_year=2019):
        """
        Initialize the roadmap generator.
        
        Args:
            start_year: First year on timeline
            end_year: Last year on timeline
            size_px: Figure size in pixels (width, height)
        """
        self.start_year = start_year
        self.end_year = end_year
        self.size_px = size_px
        self.dpi = dpi
        self.pivot_year = pivot_year
        self.years = list(years) if years is not None else None
        self.fig = None
        self.ax = None
        self.categories = {}
        self.timeline_positions = {}
        self.timeline_y_positions = {}
        self.mid_year = None
        self.color_map = {}
        
    def add_category(self, name, color):
        """Add a category (section) to the roadmap."""
        self.categories[name] = []
        self.color_map[name] = color
        
    def add_approach(self, category, year, approach_name):
        """
        Add an approach/model to a category at a specific year.
        
        Args:
            category: Category name
            year: Year to place the approach
            approach_name: Name of the approach/model
        """
        if category not in self.categories:
            raise ValueError(f"Category '{category}' not found. Add it first with add_category().")
        self.categories[category].append({'year': year, 'name': approach_name})
        
    def setup_timeline(self):
        """Calculate timeline positions."""
        years = self.years if self.years is not None else list(range(self.start_year, self.end_year + 1))
        if not years:
            raise ValueError("No years available to build timeline.")

        year_positions = np.linspace(0, 10, len(years))
        curve_t = np.linspace(-2.4, 2.4, len(years))
        tanh_curve = np.tanh(curve_t)
        tanh_range = np.ptp(tanh_curve)
        curve_height_scale = 2.4
        curve_y_offset = -0.6
        timeline_data_shift_y = (-4 / self.size_px[1]) * 5.6
        if tanh_range == 0:
            curve_y = np.zeros(len(years)) + curve_y_offset + timeline_data_shift_y
        else:
            curve_y = ((tanh_curve - tanh_curve.min()) / tanh_range) * curve_height_scale + curve_y_offset + timeline_data_shift_y

        self.timeline_positions = dict(zip(years, year_positions))
        self.timeline_y_positions = dict(zip(years, curve_y))
        self.mid_year = years[len(years) // 2]
        
    def create_roadmap(self, title="Research Roadmap", save_path=None):
        """
        Generate the roadmap visualization.
        
        Args:
            title: Title for the roadmap
            save_path: Path to save the figure (optional)
        """
        self.setup_timeline()
        figsize_in = (self.size_px[0] / self.dpi, self.size_px[1] / self.dpi)
        self.fig, self.ax = plt.subplots(figsize=figsize_in, facecolor='white')
        
        # Draw main timeline
        self._draw_timeline()

        # Draw category headers
        self._draw_category_headers()
        
        # Draw approaches by year
        self._draw_approaches()
        
        # Configure axes
        self.ax.set_xlim(-1, 11)
        self.ax.set_ylim(-2.0, 3.6)
        self.ax.axis('off')
        
        # Title
        self.fig.suptitle(title, fontsize=20, fontweight='bold', y=0.98)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
            print(f"Roadmap saved to {save_path}")
        
        return self.fig, self.ax
    
    def _draw_timeline(self):
        """Draw a horizontally elongated S-shaped timeline."""
        x_positions = list(self.timeline_positions.values())
        y_positions = [self.timeline_y_positions[year] for year in self.timeline_positions]
        
        # Draw main S-shaped curve
        self.ax.plot(x_positions, y_positions, color="#3F1800", linewidth=2, zorder=1, linestyle='--')
        
        # Draw year markers and labels
        for year, x_pos in self.timeline_positions.items():
            y_pos = self.timeline_y_positions[year]
            hex_marker = RegularPolygon(
                (x_pos, y_pos),
                numVertices=6,
                radius=0.22,
                orientation=np.pi / 6,
                facecolor="#B88C06",
                edgecolor="#3F1800",
                zorder=3,
            )
            self.ax.add_patch(hex_marker)
            self.ax.text(x_pos, y_pos, str(year), ha='center', va='center',
                       fontsize=8, fontweight='bold', color='white', zorder=4)
        
        # Draw arrow at end
        end_x = x_positions[-1]
        end_y = y_positions[-1]
        prev_x = x_positions[-2] if len(x_positions) > 1 else end_x - 0.5
        prev_y = y_positions[-2] if len(y_positions) > 1 else end_y
        direction_x = end_x - prev_x
        direction_y = end_y - prev_y
        magnitude = np.hypot(direction_x, direction_y)
        if magnitude == 0:
            direction_x, direction_y = 1.0, 0.0
            magnitude = 1.0
        unit_x = direction_x / magnitude
        unit_y = direction_y / magnitude

        arrow = FancyArrowPatch((end_x + 0.2 * unit_x, end_y + 0.2 * unit_y),
                               (end_x + 0.8 * unit_x, end_y + 0.8 * unit_y),
                               arrowstyle='->', mutation_scale=25,
                               color="#3F1800", linewidth=2, linestyle='--', zorder=2, )
        self.ax.add_patch(arrow)
    
    def _draw_approaches(self):
        """Draw all approaches grouped by category and year."""
        category_list = list(self.categories.keys())

        year_groups = {}
        for cat_idx, category_name in enumerate(category_list):
            for approach in self.categories[category_name]:
                year = approach['year']
                year_groups.setdefault(year, []).append({
                    'name': approach['name'],
                    'category_idx': cat_idx,
                    'color': self.color_map[category_name]
                })

        if not year_groups:
            return

        text_gap = 0.09
        text_height = 0.12
        base_group_offset = 0.42
        group_offset_step = 0.20
        base_highlight_pad = 0.12
        highlight_pad_step = 0.03

        year_level_map = {year: (index % 3) + 1 for index, year in enumerate(sorted(year_groups))}

        for year, approaches in year_groups.items():
            x_pos = self.timeline_positions[year]
            timeline_y = self.timeline_y_positions[year]

            approaches.sort(key=lambda x: x['category_idx'])
            if not approaches:
                continue

            place_above = year <= self.pivot_year

            level = year_level_map.get(year, 1)
            dynamic_group_offset = base_group_offset + (level - 1) * group_offset_step
            dynamic_highlight_pad = base_highlight_pad + (level - 1) * highlight_pad_step
            if year == 2012:
                dynamic_group_offset -= 0.12

            if 2020 <= year <= 2024:
                if level in (2, 3):
                    dynamic_group_offset *= 2.4 if level == 2 else 3.2

            signed_step = text_height + text_gap
            direction = 1 if place_above else -1
            text_centers = [
                timeline_y + direction * (dynamic_group_offset + app_idx * signed_step)
                for app_idx in range(len(approaches))
            ]

            for approach, y_pos in zip(approaches, text_centers):
                label = str(approach['name'])

                self.ax.text(
                    x_pos,
                    y_pos,
                    label,
                    ha='center',
                    va='center',
                    fontsize=7,
                    fontweight='500',
                    color='#1f2937',
                    bbox=dict(
                        facecolor=approach['color'],
                        edgecolor='none',
                        boxstyle=f'round,pad={dynamic_highlight_pad}',
                        alpha=0.9,
                    ),
                    zorder=6,
                )

            if place_above:
                connector_start_y = min(text_centers) - text_height / 2
            else:
                connector_start_y = max(text_centers) + text_height / 2

            self.ax.plot(
                [x_pos, x_pos],
                [connector_start_y, timeline_y],
                'gray',
                linewidth=0.9,
                linestyle='--',
                alpha=0.7,
                zorder=2,
            )

    def _draw_category_headers(self):
        """Draw category section headers in two columns with up to four rows."""
        categories = list(self.categories.keys())
        if not categories:
            return

        max_rows = 4
        col_x_positions = [2.2, 7.8]
        start_y = 3.1
        row_gap = 0.48
        box_width = 2.8
        box_height = 0.36

        for idx, category_name in enumerate(categories):
            col_idx = min(idx // max_rows, 1)
            row_idx = idx % max_rows
            x_pos = col_x_positions[col_idx]
            y_pos = start_y - row_idx * row_gap
            color = self.color_map.get(category_name, '#E6F1FB')

            box = FancyBboxPatch(
                (x_pos - box_width / 2, y_pos - box_height / 2),
                box_width,
                box_height,
                boxstyle="round,pad=0",
                edgecolor='none',
                facecolor=color,
                linewidth=0,
                zorder=5,
            )
            self.ax.add_patch(box)

            self.ax.text(
                x_pos,
                y_pos,
                category_name,
                ha='center',
                va='center',
                fontsize=7,
                fontweight='bold',
                zorder=6,
            )
    
    def show(self):
        """Display the roadmap."""
        plt.show()


def _resolve_column_name(df, candidates):
    for column_name in candidates:
        if column_name in df.columns:
            return column_name
    raise KeyError(f"Missing required columns. Expected one of: {candidates}")


def _normalize_category_text(text):
    value = str(text).strip()
    if "—" in value:
        value = value.split("—", 1)[0].strip()
    return " ".join(value.split()[:5])


def _normalize_approach_group(text):
    return str(text).strip().lower()


def _truncate_approach_ai(text):
    value = str(text).strip()
    return re.split(r"[\(\+/\]]", value, maxsplit=1)[0].strip()


def _word_count(text):
    return len([word for word in str(text).strip().split() if word])


def plot_timeline(df):
    required_year_col = _resolve_column_name(df, ["Year"])
    required_approach_ai_col = _resolve_column_name(df, ["Approach (ai)", "Approach ai", "Approach (AI)"])
    required_approach_group_col = _resolve_column_name(df, ["Approach group", "Approach Group"])
    required_category_col = _resolve_column_name(df, ["Category (section)", "Category section", "Category Section"])

    cleaned = df[[required_year_col, required_approach_ai_col, required_approach_group_col, required_category_col]].copy()
    cleaned[required_year_col] = pd.to_numeric(cleaned[required_year_col], errors="coerce")
    cleaned[required_year_col] = np.floor(cleaned[required_year_col]).astype("Int64")
    for col in (required_approach_ai_col, required_approach_group_col, required_category_col):
        cleaned[col] = cleaned[col].fillna("").astype(str).str.strip()

    valid_mask = (
        cleaned[required_year_col].notna()
        & ~cleaned[required_approach_group_col].isin({"", "-"})
        & ~cleaned[required_category_col].isin({"", "-"})
    )
    cleaned = cleaned[valid_mask].copy()

    if cleaned.empty:
        raise ValueError("No valid rows available for timeline plot after filtering.")

    cleaned[required_category_col] = cleaned[required_category_col].map(_normalize_category_text)

    group_norm = cleaned[required_approach_group_col].map(_normalize_approach_group)
    should_truncate = group_norm.isin(TRUNCATE_GROUPS)

    cleaned["_approach_timeline"] = cleaned[required_approach_group_col]
    truncated_ai = cleaned.loc[should_truncate, required_approach_ai_col].map(_truncate_approach_ai)
    truncated_ai = truncated_ai.where(
        truncated_ai.map(_word_count).le(3),
        cleaned.loc[should_truncate, required_approach_group_col],
    )
    cleaned.loc[should_truncate, "_approach_timeline"] = truncated_ai.where(
        truncated_ai.ne(""),
        cleaned.loc[should_truncate, required_approach_group_col],
    )
    cleaned["_approach_timeline"] = cleaned["_approach_timeline"].replace("", np.nan)
    cleaned = cleaned[cleaned["_approach_timeline"].notna()].copy()

    aggregated = (
        cleaned
        .groupby([required_year_col, required_category_col, "_approach_timeline"])
        .size()
        .reset_index(name="count")
    )
    aggregated = aggregated.sort_values(
        by=[required_year_col, required_category_col, "count", "_approach_timeline"],
        ascending=[True, True, False, True],
    )
    top_per_year_category = aggregated.drop_duplicates(
        subset=[required_year_col, required_category_col],
        keep="first",
    ).copy()

    if top_per_year_category.empty:
        raise ValueError("No valid rows available for timeline plot after top-per-category filtering.")

    dataset_years = sorted(int(y) for y in top_per_year_category[required_year_col].dropna().unique())
    start_year = dataset_years[0]
    end_year = dataset_years[-1]

    category_order = list(dict.fromkeys(top_per_year_category[required_category_col]))

    roadmap = RoadmapGenerator(
        start_year=start_year,
        end_year=end_year,
        years=dataset_years,
        size_px=TIMELINE_SIZE_PX,
    )
    for index, category_name in enumerate(category_order):
        roadmap.add_category(category_name, PALETTE[index % len(PALETTE)])

    compact_rows = top_per_year_category.rename(
        columns={
            required_year_col: "year",
            required_category_col: "category",
            "_approach_timeline": "approach",
        }
    )
    for row in compact_rows.itertuples(index=False):
        roadmap.add_approach(
            row.category,
            int(row.year),
            row.approach,
        )

    roadmap.create_roadmap(
        title=f"Approach Timeline by Category ({start_year}-{end_year})",
    )

    save_with_plot_border(
        roadmap.fig,
        png_path=OUTPUT_DIR / "timeline_approach_category.png",
        pdf_path=OUTPUT_DIR / "timeline_approach_category.pdf",
        dpi=TIMELINE_EXPORT_DPI,
        bbox_inches="tight",
    )

    return roadmap.fig, roadmap.ax