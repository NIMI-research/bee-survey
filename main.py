from pathlib import Path
import logging

from data_loader import LiteratureDataset
from visualization.year_category_pies import plot_yearly_category_pies
from visualization.count_category_over_years import count_category_over_years
from visualization.violin_category import plot_category_violin
from visualization.bubble_approach import plot_category_approach_bubble
from visualization.sankey_flow import plot_category_approach_sankey 
from visualization.heatmap_approach import heatmap_subcat_approach_by_category
from visualization.word_cloud_search import plot_keyword_wordcloud
from visualization.sankey_flow_complex import plot_modality_approach_category_sankey
from visualization.hierarchy import plot_category_approach_hierarchy
from visualization.nodes_approach_category import plot_nodes_approach_category
from visualization.count_category_over_years import count_category_over_years
from visualization.category_approach_bar import count_approach_over_category

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
def main():

    dataset = LiteratureDataset()
    df = dataset.load()
    logger.info(f"Dataset loaded successfully with {len(df)} records")

    logger.info("Generating: Yearly Category Pies")
    plot_yearly_category_pies(df)
    logger.info("Generating: Count Category Over Years")
    count_category_over_years(df)
    logger.info("Generating: Category Violin Plot")
    plot_category_violin(df)
    logger.info("Generating: Category Approach Bubble Plot")
    plot_category_approach_bubble(df)
    logger.info("Generating: Category Approach Sankey Flow")
    plot_category_approach_sankey(df)
    logger.info("Generating: Category Approach Heatmap")
    heatmap_subcat_approach_by_category(df)  
    logger.info("Generating: Keyword Word Cloud")
    plot_keyword_wordcloud(df)
    logger.info("Generating: Modality Approach Category Sankey")
    plot_modality_approach_category_sankey(df)
    logger.info("Generating: Category Approach Hierarchy")
    plot_category_approach_hierarchy(df)
    logger.info("Generating: Nodes Approach Category")
    plot_nodes_approach_category(df)
    logger.info("Generating: Count Approach Over category")
    count_approach_over_category(df)

    logger.info("All plots completed successfully")

if __name__ == "__main__":
    main()