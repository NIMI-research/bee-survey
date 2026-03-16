from data_loader import LiteratureDataset
from visualization.year_category_pies import plot_yearly_category_pies

def main():

    dataset = LiteratureDataset()
    df = dataset.load()


    plot_yearly_category_pies(df)

if __name__ == "__main__":
    main()