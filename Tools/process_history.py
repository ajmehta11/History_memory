import json
import os
from pathlib import Path

from scraping_pipeline import scrape_to_json
from json2vectordb import ingest_product_to_azure_search


def process_history(history_file="history.json", output_dir="output", final_json="final.json"):

    with open(history_file, 'r') as f:
        history = json.load(f)

    print(f"Loaded {len(history)} items from {history_file}\n")

    # Collect all successfully processed products
    all_products = []

    for idx, item in enumerate(history, 1):
        url = item.get('url')
        if not url:
            print(f"[{idx}/{len(history)}] Skipping item with no URL")
            continue

        last_visit_time = item.get('lastVisitTime')

        print(f"\n{'='*80}")
        print(f"Processing [{idx}/{len(history)}]: {url}")
        print(f"{'='*80}\n")

        try:
            product_json = scrape_to_json(url, output_dir=output_dir, last_visit_time=last_visit_time)

            if product_json.get("is_product") != "Yes":
                print(f"\n⊘ Not a product, skipping upload to Azure AI Search\n")
                continue

            print(f"\n==== Uploading to Azure AI Search ====\n")
            ingest_product_to_azure_search(product_json)

            # Add to collection
            all_products.append(product_json)

            print(f"\n✓ Successfully processed: {url}\n")

        except Exception as e:
            print(f"\n✗ Error processing {url}: {e}\n")
            continue

    # Save all products to final.json
    with open(final_json, 'w') as f:
        json.dump(all_products, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*80}")
    print(f"Completed processing {len(history)} items")
    print(f"Saved {len(all_products)} products to {final_json}")
    print(f"{'='*80}\n")


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
    parser.add_argument(
        "--final-json",
        default="final.json",
        help="Output file for all processed products (default: final.json)"
    )

    args = parser.parse_args()
    process_history(args.history, args.out, args.final_json)