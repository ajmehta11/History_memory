import azure.functions as func
import logging

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

    for i, item in enumerate(data[:10], start=1):
        title = item.get("title") or "No Title"
        url = item.get("url", "")
        logging.info("%d. %s | %s", i, title, url)

    return func.HttpResponse("ok", status_code=200)
