import pandas as pd
import plotly.graph_objects as go

from const import CATEGORY_COLORS, FALLBACK_CATEGORY_COLOR, OUTPUT_DIR

def plot_approach_timeline(df):
    """
    Create a horizontal timeline from min(Year) to max(Year) with approaches pointing to each Year.
    Text boxes are colored by Category.
    
    df: DataFrame with columns ["Year", "Approach Group", "Category"]
    """
    # count publications per Year & approach group
    counts = df.groupby(["Year", "Approach Group", "Subcategory (ai task)"]).size().reset_index(name="count")
    
    # Determine timeline range
    min_Year = df["Year"].min()
    max_Year = df["Year"].max()
    Years = list(range(min_Year, max_Year + 1))
    
    # Create figure
    fig = go.Figure()
    
    # Draw horizontal timeline at y=0
    fig.add_shape(
        type="line",
        x0=min_Year, x1=max_Year, y0=0, y1=0,
        line=dict(color="black", width=3)
    )
    
    # Add Year labels on the line
    for Year in Years:
        fig.add_annotation(
            x=Year,
            y=0,
            text=str(Year),
            showarrow=False,
            yshift=-15,
            font=dict(color="black", size=12),
            xanchor="center"
        )
    
    # Add approach annotations pointing to the timeline
    y_spacing = 0.25  # vertical spacing for approaches
    for Year in Years:
        Year_data = counts[counts["Year"] == Year]
        for i, row in enumerate(Year_data.itertuples()):
            fig.add_annotation(
                x=Year,
                y=(i + 1) * y_spacing,  # stagger approaches above the line
                ax=Year,
                ay=0,
                xanchor="center",
                yanchor="bottom",
                text=f"{row._2} ({row.count})",  # row._2 is "Approach Group" in namedtuple
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=1,
                arrowcolor="black",
                bgcolor=CATEGORY_COLORS.get(row._3, FALLBACK_CATEGORY_COLOR),
                bordercolor="black",
                borderwidth=1,
                font=dict(color="white")
            )
    
    # Update layout for pure timeline style
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis=dict(visible=False, range=[min_Year - 1, max_Year + 1]),
        yaxis=dict(visible=False),
        showlegend=False,
        height=400 + len(df) * 20,
        width=1000,
        margin=dict(t=100, b=150)
    )
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    fig.write_image(OUTPUT_DIR / "timeline_approach.pdf")