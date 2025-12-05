import json
import os
import logging
from pathlib import Path
from datetime import datetime

from azure.storage.blob import BlobServiceClient

from scraping_pipeline import scrape_to_json
from json2vectordb import ingest_product_to_azure_search


def upload_to_blob_storage(data, blob_name="final.json"):
    """
    Upload JSON data to Azure Blob Storage
    """
    try:
        connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        container_name = os.environ.get("BLOB_CONTAINER_NAME", "history-products")

        if not connection_string:
            logging.error("AZURE_STORAGE_CONNECTION_STRING not found in environment variables")
            return None

        # Create blob service client
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)

        # Get container client
        container_client = blob_service_client.get_container_client(container_name)

        # Create container if it doesn't exist
        try:
            container_client.create_container()
            logging.info(f"Created container: {container_name}")
        except Exception:
            # Container already exists
            pass

        # Generate blob name with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        blob_name_with_timestamp = f"final_{timestamp}.json"

        # Upload the data
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name_with_timestamp
        )

        json_data = json.dumps(data, indent=2, ensure_ascii=False)
        blob_client.upload_blob(json_data, overwrite=True)

        logging.info(f"Successfully uploaded to blob storage: {blob_name_with_timestamp}")
        return blob_name_with_timestamp

    except Exception as e:
        logging.error(f"Error uploading to blob storage: {e}")
        raise


def process_history(history_data, output_dir="/tmp/output"):
    """
    Process history data through scraping pipeline and upload to Azure AI Search

    Args:
        history_data: List of history items (dict with 'url' and optionally 'lastVisitTime')
        output_dir: Directory for temporary output files (default: /tmp/output for Linux)

    Returns:
        dict: Summary of processing results
    """
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    logging.info(f"Processing {len(history_data)} history items")

    # Collect all successfully processed products
    all_products = []
    stats = {
        "total": len(history_data),
        "processed": 0,
        "products": 0,
        "non_products": 0,
        "errors": 0
    }

    for idx, item in enumerate(history_data, 1):
        url = item.get('url')
        if not url:
            logging.warning(f"[{idx}/{len(history_data)}] Skipping item with no URL")
            stats["errors"] += 1
            continue

        last_visit_time = item.get('lastVisitTime')

        logging.info(f"{'='*80}")
        logging.info(f"Processing [{idx}/{len(history_data)}]: {url}")
        logging.info(f"{'='*80}")

        try:
            product_json = scrape_to_json(url, output_dir=output_dir, last_visit_time=last_visit_time)
            stats["processed"] += 1

            if product_json.get("is_product") != "Yes":
                logging.info(f"Not a product, skipping upload to Azure AI Search")
                stats["non_products"] += 1
                continue

            logging.info(f"Uploading to Azure AI Search")
            ingest_product_to_azure_search(product_json)

            # Add to collection
            all_products.append(product_json)
            stats["products"] += 1

            logging.info(f"Successfully processed: {url}")

        except Exception as e:
            logging.error(f"Error processing {url}: {e}", exc_info=True)
            stats["errors"] += 1
            continue

    # Upload to blob storage
    blob_name = None
    if all_products:
        try:
            blob_name = upload_to_blob_storage(all_products)
            logging.info(f"Uploaded {len(all_products)} products to blob storage")
        except Exception as e:
            logging.error(f"Failed to upload to blob storage: {e}")

    # Summary
    logging.info(f"{'='*80}")
    logging.info(f"Processing complete:")
    logging.info(f"  Total items: {stats['total']}")
    logging.info(f"  Successfully processed: {stats['processed']}")
    logging.info(f"  Products found: {stats['products']}")
    logging.info(f"  Non-products: {stats['non_products']}")
    logging.info(f"  Errors: {stats['errors']}")
    logging.info(f"  Blob name: {blob_name}")
    logging.info(f"{'='*80}")

    return {
        "stats": stats,
        "blob_name": blob_name,
        "products": all_products
    }
