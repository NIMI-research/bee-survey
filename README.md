# Bee Survey Data Analysis

This project provides a comprehensive suite of tools to load, analyze, and visualize literature survey data for bee research. The main entry point is `main.py`.

## Features

- Generate literature datasets using `data_builder`
- Load and process survey data with `data_loader`
- Display dataset overview and basic statistics
- Generate 20 diverse visualizations for data analysis and exploration

## Workflow

**If input is an Excel workbook with multiple subset sheets:**

1. **Run `data_builder.py` first** to consolidate and standardize the data from multiple sheets (e.g., "New-original 2024-2025", "Pass", "Original", "original-2011-2023") into a uniform CSV format (`MAIN_CSV_PATH`)
2. **Then run `main.py`** to load the consolidated CSV and generate visualizations

**If input is already a prepared CSV:**

- Simply run `main.py` directly

The `data_builder` merges multiple subset sheets, deduplicates records, reconciles with the Sources sheet (treating it as ground truth), and outputs a single standardized CSV that `main.py` can process.

## Project Structure

```
bee-survey/
├── main.py                          # Entry point for running the application
├── data_builder.py                  # Build and prepare datasets
├── data_loader.py                   # Load CSV data and manage data pipelines
├── const.py                         # Project constants and configuration
├── utils.py                         # Utility functions
├── requirements.txt                 # Python dependencies
│
├── input/                           # Input data directory
│   ├── Bee-Me Literature Review_Main.csv
│   └── Visualization.csv
│
├── output/                          # Generated outputs directory
│
└── visualization/                   # Visualization scripts
    ├── bee_demographic.py           # Demographic analysis charts
    ├── bee_demographic_bar.py       # Bar chart demographics
    ├── bubble_approach.py           # Bubble chart analysis
    ├── bubble_vista.py              # Bubble chart variants
    ├── category_approach_bar.py     # Category bar charts
    ├── choloropleth_bee.py          # Choropleth maps
    ├── count_category_over_years.py # Category counts over time
    ├── demographic_migrations.py    # Migration pattern analysis
    ├── demographic_relations.py     # Demographic relationships
    ├── heatmap_approach.py          # Heatmap visualizations
    ├── hierarchy.py                 # Hierarchical visualizations
    ├── nodes_approach_category.py   # Node-based category analysis
    ├── ridge_category_years.py      # Ridge plots by category
    ├── sankey_flow.py               # Sankey diagram flows
    ├── sankey_flow_complex.py       # Complex Sankey flows
    ├── stacked_category_approach.py # Stacked category charts
    ├── timeline_category_n_approach.py # Timeline analysis
    ├── violin_category.py           # Violin plots
    ├── word_cloud_search.py         # Word cloud generation
    └── year_category_pies.py        # Pie charts by year
```


### Using Conda

1. Create the environment:

```bash
conda create -n bee-survey python=3.11
```

2. Activate the environment:
```bash
conda activate bee-survey
```
3. Install dependencies:
```bash
pip install -r requirements.txt
```
