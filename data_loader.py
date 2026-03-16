import pandas as pd
from pathlib import Path
from const import MAIN_CSV_PATH
from data_builder import build_main_csv, normalize_category


class LiteratureDataset:

    def __init__(self, csv_path=MAIN_CSV_PATH):
        self.csv_path = Path(csv_path)
        self.df = None

    def ensure_dataset(self):
        """Build CSV if it does not exist."""
        if not self.csv_path.exists():
            build_main_csv(output_path=self.csv_path)

    def load(self):
        """Load CSV as pandas DataFrame."""
        self.ensure_dataset()
        self.df = pd.read_csv(self.csv_path)

        if "Approach Group" not in self.df.columns:
            raise ValueError(
                f"Required column 'Approach Group' is missing in CSV: {self.csv_path}"
            )

        self.df["Approach Group"] = (
            self.df["Approach Group"].fillna("").astype(str).str.strip()
        )

        self.df["Approach Group"] = self.df["Approach Group"].apply(
            lambda value: [part.strip() for part in value.split("/") if part.strip()]
            if value
            else [""]
        )
        self.df = self.df.explode("Approach Group", ignore_index=True)

        self.df["Category"] = self.df.apply(normalize_category, axis=1)
        return self.df

    def get(self):
        """Return dataframe without reloading."""
        if self.df is None:
            return self.load()
        return self.df