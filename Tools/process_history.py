import json
import os
from pathlib import Path

from scraping_pipeline import scrape_to_json
from json2vectordb import ingest_product_to_azure_search


def process_history(history_data, output_dir="/Users/aryanmehta/Desktop/History_memory/Tools/output"):
    """
    Process history data (list of URLs) through scraping pipeline

    Args:
        history_data: List of dicts with 'url' and optionally 'lastVisitTime'
        output_dir: Output directory for intermediate files

    Returns:
        dict with stats: total, processed, products, non_products, errors
    """
    history = history_data
    print(f"Processing {len(history)} items\n")

    # Collect all successfully processed products
    all_products = []

    stats = {
        "total": len(history),
        "processed": 0,
        "products": 0,
        "non_products": 0,
        "errors": 0
    }

    for idx, item in enumerate(history, 1):
        url = item.get('url')
        if not url:
            print(f"[{idx}/{len(history)}] Skipping item with no URL")
            stats["errors"] += 1
            continue

        last_visit_time = item.get('lastVisitTime')

        print(f"\n{'='*80}")
        print(f"Processing [{idx}/{len(history)}]: {url}")
        print(f"{'='*80}\n")

        try:
            product_json = scrape_to_json(url, output_dir=output_dir, last_visit_time=last_visit_time)
            stats["processed"] += 1

            if product_json.get("is_product") != "Yes":
                print(f"\n⊘ Not a product, skipping upload to Azure AI Search\n")
                stats["non_products"] += 1
                continue

            print(f"\n==== Uploading to Azure AI Search ====\n")
            ingest_product_to_azure_search(product_json)

            # Add to collection
            all_products.append(product_json)
            stats["products"] += 1

            print(f"\n✓ Successfully processed: {url}\n")

        except Exception as e:
            print(f"\n✗ Error processing {url}: {e}\n")
            stats["errors"] += 1
            continue

    print(f"\n{'='*80}")
    print(f"Completed processing {len(history)} items")
    print(f"Products: {stats['products']}, Non-products: {stats['non_products']}, Errors: {stats['errors']}")
    print(f"{'='*80}\n")

    return {
        "stats": stats,
        "products": all_products,
        "blob_name": None
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Process all URLs from history.json through scraping pipeline and upload to Azure AI Search"
    )
    parser.add_argument(
        "--history",
        default="history.json",
        help="Path to history.json file (default: history.json)"
    )
    parser.add_argument(
        "--out",
        default="output",
        help="Output directory for intermediate files (default: output)"
    )

    args = parser.parse_args()

    # Load history data from file
    with open(args.history, 'r') as f:
        history_data = json.load(f)

    # Process the data
    result = process_history(history_data, args.out)
    print(f"\nFinal stats: {result['stats']}")