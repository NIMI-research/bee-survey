# Bee Survey Data Analysis

This project provides tools to load, analyze, and visualize literature survey data for bee research. The main entry point is `main.py`.

## Features

- Collect and preprocess papers from different sources into a single dataset using `data_preprocessor.py`.
- Display dataset overview and basic statistics.
- Generate 7 visualizations for analysis (5 of which are used in the paper).

## Data Pipeline

1. Papers collected from different sources are combined by `data_preprocessor.py` into `Bee-Me Literature Review_Main.csv`.
2. When new papers are added, append them to `Bee-Me Literature Review_Main.csv` and re-run preprocessing to regenerate `visualizations.csv`.
3. `visualizations.csv` is the dataset consumed by the plotting scripts.

## Setup
Project Structure:
```
bee-survey/
├── src/
├──── main.py
├──── data_preprocessor.py
├──── data_loader.py
├──── visualization/
├── input/
├──── <Bee-Me Literature Review_Main.csv>
├──── <Visualizations.csv>
├── output/
└───── visualizations/
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
