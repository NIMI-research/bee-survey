from pathlib import Path
import logging
from data_loader import LiteratureDataset
from visualization.year_category_pies import plot_yearly_category_pies
from visualization.count_category_over_years import count_category_over_years
from visualization.bubble_approach import plot_category_approach_bubble
from visualization.word_cloud_search import plot_keyword_wordcloud
from visualization.sankey_flow_complex import plot_modality_approach_category_sankey
from visualization.hierarchy import plot_category_approach_hierarchy
from visualization.count_category_over_years import count_category_over_years
from visualization.stacked_category_approach import count_approach_over_category
from visualization.choloropleth_bee import plot_choropleth_country
from visualization.ridge_category_years import ridge_plot_approaches_over_years
from visualization.bee_demographic_bar import plot_bar_bee_demographic
from visualization.demographic_migrations import plot_circular_migration_bee_research
####Configure logging
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
    logger.info("Generating: Category Approach Bubble Plot")
    plot_category_approach_bubble(df)
    logger.info("Generating: Keyword Word Cloud")
    plot_keyword_wordcloud(df)
    logger.info("Generating: Modality Approach Category Sankey")
    plot_modality_approach_category_sankey(df)
    logger.info("Generating: Category Approach Hierarchy")
    plot_category_approach_hierarchy(df)
    logger.info("Generating: Stacked Approach Over category")
    count_approach_over_category(df)
    logger.info("Generating: Choropleth Country")
    plot_choropleth_country(df)
    logger.info("Generating: Bar Plot - Bee Demographic")
    plot_bar_bee_demographic(df)
    logger.info("Generating: Circular Migration - Bee to Research")
    plot_circular_migration_bee_research(df)
    logger.info("Generating: Ridge Plot - Approaches Over Years")
    ridge_plot_approaches_over_years(df)

if __name__ == "__main__":
    main()