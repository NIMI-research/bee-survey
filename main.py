from data_loader import LiteratureDataset
from visualization.year_category_pies import plot_yearly_category_pies
from visualization.count_category_over_years import count_category_over_years
from visualization.violin_category import plot_category_violin
from visualization.timeline_category_n_approach import plot_approach_timeline
from visualization.bubble_approach import plot_category_approach_bubble
from visualization.sankey_flow import plot_category_approach_sankey 
from visualization.heatmap_approach import plot_category_approach_heatmap
def main():

    dataset = LiteratureDataset()
    df = dataset.load()


    # plot_yearly_category_pies(df)
    # count_category_over_years(df)
    # plot_category_violin(df)
    plot_category_approach_bubble(df)
    plot_category_approach_sankey(df)
    plot_category_approach_heatmap(df)  

if __name__ == "__main__":
    main()