import azure.functions as func
import logging
import json
import os
from datetime import datetime
from azure.storage.blob import BlobServiceClient

app = func.FunctionApp()

@app.route(
    route="ingestHistory",
    auth_level=func.AuthLevel.ANONYMOUS,
    methods=["POST"]
)
def ingestHistory(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("ingestHistory function triggered")

    try:
        data = req.get_json()
    except ValueError:
        logging.exception("Failed to parse JSON body")
        return func.HttpResponse("Invalid JSON", status_code=400)

    if not isinstance(data, list):
        logging.warning("Request JSON is not a list")
        return func.HttpResponse(
            "Expected a JSON array of history items",
            status_code=400
        )

    logging.info("Received %d history items", len(data))

    for i, item in enumerate(data, start=1):
        url = item.get("url", "")
        title = item.get("title", "")
        logging.info(f"[{i}] URL: {url}")
        logging.info(f"[{i}] Title: {title}")

    try:
        connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        container_name = os.environ.get("BLOB_CONTAINER_NAME", "history-products")

        if not connection_string:
            logging.error("AZURE_STORAGE_CONNECTION_STRING not found")
            return func.HttpResponse(
                json.dumps({"status": "error", "message": "Storage not configured"}),
                status_code=500,
                mimetype="application/json"
            )

        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)

        try:
            container_client.create_container()
            logging.info(f"Created container: {container_name}")
        except Exception:
            pass 

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        blob_name = f"pending/history_{timestamp}.json"

        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )

        json_data = json.dumps(data, indent=2, ensure_ascii=False)
        blob_client.upload_blob(json_data, overwrite=True)

        logging.info(f"Saved {len(data)} URLs to blob: {blob_name}")

        response_data = {
            "status": "success",
            "message": f"Saved {len(data)} history items for processing",
            "blob_name": blob_name,
            "count": len(data)
        }

        return func.HttpResponse(
            json.dumps(response_data, indent=2),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"Error saving to blob storage: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "message": str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )
