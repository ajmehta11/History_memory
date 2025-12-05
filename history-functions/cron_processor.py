import json
import os
import sys
from datetime import datetime
from pathlib import Path
import io

settings_path = Path(__file__).parent / "local.settings.json"
if settings_path.exists():
    with open(settings_path) as f:
        settings = json.load(f)
        for key, value in settings.get("Values", {}).items():
            if key not in os.environ:
                os.environ[key] = value

# Now import everything else
import logging
from azure.storage.blob import BlobServiceClient

# Add Tools directory to path for imports
tools_dir = Path(__file__).parent.parent / "Tools"
if tools_dir.exists():
    sys.path.insert(0, str(tools_dir))

from process_history import process_history

try:
    from compute_preferences import get_all_products, compute_preferences
    COMPUTE_PREFERENCES_AVAILABLE = True
except ImportError:
    COMPUTE_PREFERENCES_AVAILABLE = False

# Setup logging
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f"cron_processor_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)

# Silence Azure SDK verbose logging
logging.getLogger("azure").setLevel(logging.WARNING)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)


class LoggerWriter:
    """Redirect print statements to logger"""
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level

    def write(self, message):
        if message and message.strip():
            self.logger.log(self.level, message.strip())

    def flush(self):
        pass


def get_pending_blobs(blob_service_client, container_name):
    """Get list of pending blob files to process"""
    logging.info("Getting list of pending blobs from container...")
    container_client = blob_service_client.get_container_client(container_name)

    try:
        # List all blobs in the "pending" folder
        logging.info("Listing blobs with prefix 'pending/'...")
        blobs = container_client.list_blobs(name_starts_with="pending/")
        blob_list = [blob.name for blob in blobs if blob.name.endswith('.json')]
        logging.info(f"Found {len(blob_list)} pending blob(s): {blob_list}")
        return blob_list
    except Exception as e:
        logging.error(f"Error listing blobs: {e}")
        return []


def download_blob(blob_service_client, container_name, blob_name):
    """Download blob content as JSON"""
    logging.info(f"Downloading blob: {blob_name}")
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

    try:
        blob_data = blob_client.download_blob().readall()
        logging.info(f"Downloaded {len(blob_data)} bytes")
        data = json.loads(blob_data)
        logging.info(f"Parsed JSON successfully: {len(data)} items")
        return data
    except Exception as e:
        logging.error(f"Error downloading blob {blob_name}: {e}")
        return None


def move_blob(blob_service_client, container_name, source_blob_name, dest_folder="processed"):
    """Move blob from pending to processed folder"""
    filename = Path(source_blob_name).name
    dest_blob_name = f"{dest_folder}/{filename}"

    logging.info(f"Moving blob from {source_blob_name} to {dest_blob_name}")

    source_client = blob_service_client.get_blob_client(container=container_name, blob=source_blob_name)
    dest_client = blob_service_client.get_blob_client(container=container_name, blob=dest_blob_name)

    try:
        # Copy blob
        logging.info(f"Copying blob to '{dest_folder}/' folder...")
        dest_client.start_copy_from_url(source_client.url)

        # Delete source blob
        logging.info("Deleting source blob from 'pending/' folder...")
        source_client.delete_blob()

        logging.info(f"Successfully moved blob to {dest_blob_name}")
    except Exception as e:
        logging.error(f"Error moving blob {source_blob_name}: {e}")


def update_user_preferences():
    """Update user preferences based on products in Azure AI Search"""
    if not COMPUTE_PREFERENCES_AVAILABLE:
        logging.info("Skipping preference computation (compute_preferences module not available)")
        return

    try:
        logging.info("\n" + "="*80)
        logging.info("Updating user preferences")
        logging.info("="*80)

        # Redirect stdout to logger
        old_stdout = sys.stdout
        sys.stdout = LoggerWriter(logging.getLogger(), logging.INFO)

        try:
            # Fetch products from Azure AI Search
            logging.info("Fetching products from Azure AI Search...")
            products = get_all_products()
            logging.info(f"Retrieved {len(products)} products")

            if not products:
                logging.info("No products found - skipping preference computation")
                return

            # Compute preferences
            logging.info("Computing preferences...")
            preferences = compute_preferences(products)
        finally:
            sys.stdout = old_stdout

        # Save to user_preferences.json
        output_path = Path(__file__).parent.parent / "Tools" / "user_preferences.json"
        with open(output_path, 'w') as f:
            json.dump(preferences, f, indent=2, ensure_ascii=False)

        logging.info(f"Updated user preferences file at {output_path}")
        logging.info("Preferences summary:")
        logging.info(f"  Total products: {preferences['total_products']}")
        logging.info(f"  Top categories: {', '.join(preferences['top_categories'][:5])}")
        logging.info(f"  Top brands: {', '.join(preferences['top_brands'][:5])}")
        logging.info(f"  Top colors: {', '.join(preferences['top_colors'][:5])}")

    except Exception as e:
        logging.error(f"Error updating user preferences: {e}", exc_info=True)


def main():
    """Main processing function"""
    logging.info("="*80)
    logging.info("Starting cron processor")
    logging.info(f"Time: {datetime.now()}")
    logging.info("="*80)

    # Get Azure Storage configuration
    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    container_name = os.environ.get("BLOB_CONTAINER_NAME", "history-products")

    if not connection_string:
        logging.error("AZURE_STORAGE_CONNECTION_STRING not found in environment variables")
        return

    # Create blob service client
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)

    # Get pending blobs
    pending_blobs = get_pending_blobs(blob_service_client, container_name)

    processed_any = False

    if not pending_blobs:
        logging.info("No pending blobs to process")
    else:
        logging.info(f"Found {len(pending_blobs)} pending blob(s) to process")

        # Process each blob
        for idx, blob_name in enumerate(pending_blobs, 1):
            logging.info("\n" + "="*80)
            logging.info(f"Processing blob {idx}/{len(pending_blobs)}: {blob_name}")
            logging.info("="*80)

            # Download blob content
            history_data = download_blob(blob_service_client, container_name, blob_name)

            if not history_data:
                logging.error(f"Failed to download blob {blob_name}, skipping")
                continue

            logging.info(f"Downloaded {len(history_data)} URL(s) from blob")

            # Log the URLs we're about to process
            for i, item in enumerate(history_data, 1):
                url = item.get('url', 'NO URL')
                title = item.get('title', 'NO TITLE')
                logging.info(f"[{i}] URL: {url}")
                logging.info(f"     Title: {title}")

            # Process the history data
            try:
                logging.info(f"Starting to process {len(history_data)} URL(s)...")
                logging.info("This will scrape each URL and upload products to Azure AI Search")

                # Redirect stdout to logger so print statements appear in logs
                old_stdout = sys.stdout
                sys.stdout = LoggerWriter(logging.getLogger(), logging.INFO)

                try:
                    result = process_history(history_data)
                finally:
                    sys.stdout = old_stdout

                logging.info("Processing complete")
                logging.info(f"Stats - Total items: {result['stats']['total']}")
                logging.info(f"Stats - Products found: {result['stats']['products']}")
                logging.info(f"Stats - Non-products: {result['stats']['non_products']}")
                logging.info(f"Stats - Errors: {result['stats']['errors']}")

                if result['stats']['products'] > 0:
                    logging.info(f"{result['stats']['products']} product(s) uploaded to Azure AI Search")
                    processed_any = True
                else:
                    logging.warning("No products were uploaded to Azure AI Search")

                # Move blob to processed folder
                move_blob(blob_service_client, container_name, blob_name, "processed")

            except Exception as e:
                logging.error(f"Error processing blob {blob_name}: {e}", exc_info=True)
                # Move to failed folder
                logging.info("Moving failed blob to 'failed/' folder")
                move_blob(blob_service_client, container_name, blob_name, "failed")

    # Update user preferences if we processed any products
    if processed_any:
        logging.info("Products were added; updating user preferences")
        update_user_preferences()
    elif not pending_blobs:
        logging.info("No new products, but updating preferences anyway")
        update_user_preferences()

    logging.info("\n" + "="*80)
    logging.info("Cron processor completed successfully")
    logging.info("="*80)


if __name__ == "__main__":
    main()
