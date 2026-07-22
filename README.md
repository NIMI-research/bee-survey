# Bee Survey Data Analysis

This project provides tools to load, analyze, and visualize literature survey data for bee research. The main entry point is `main.py`.

## Features

- Collect and preprocess papers from different sources into a single dataset using `data_preprocessor.py`, which produces `main.csv`.
- `main.csv` is then processed into `visualizations.csv`, the dataset used for plotting.
- Display dataset overview and basic statistics.
- Generate 7 visualizations for analysis (4 of which are used in the paper).

## Data Pipeline

1. Papers collected from different sources are combined by `data_preprocessor.py` into `main.csv`.
2. When new papers are added, append them to `main.csv` and re-run preprocessing to regenerate `visualizations.csv`.
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
├──── [text](<Bee-Me Literature Review_Main.csv>)
├──── [text](<Bee-Me Literature Reviewcsv>)
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