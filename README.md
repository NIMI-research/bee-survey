# Bee Survey Data Analysis

This project provides tools to load, analyze, and visualize literature survey data for bee research. The main entry point is `main.py`.

## Features

- Generate literature dataset using `data_builder`.
- Display dataset overview and basic statistics.
- Generate visualizations (e.g., pie charts per year) for analysis.

## Setup
Project Structure:
bee-survey/
├── main.py
├── data_loader.py
├── input/
├──── (<Bee-Me Literature Review_Main.csv>)
├──── (<Bee-Me Literature Reviewcsv>)
├── output/
└───── visualizations/



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
