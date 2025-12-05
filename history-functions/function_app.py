import azure.functions as func
import logging
import json

from process_history import process_history

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

    # Log first 10 items for debugging
    for i, item in enumerate(data[:10], start=1):
        title = item.get("title") or "No Title"
        url = item.get("url", "")
        logging.info("%d. %s | %s", i, title, url)

    # Process the history data
    try:
        logging.info("Starting history processing...")
        result = process_history(data)

        response_data = {
            "status": "success",
            "message": f"Processed {result['stats']['products']} products",
            "stats": result['stats'],
            "blob_name": result['blob_name']
        }

        logging.info("Processing completed successfully")
        return func.HttpResponse(
            json.dumps(response_data, indent=2),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"Error processing history: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "message": str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )
