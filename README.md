# History Memory - Shopping Assistant

A personal shopping assistant that learns from your browsing history. Captures URLs from a browser extension, scrapes product data, and enables semantic search through an AI agent.

## Architecture

### 1. Web Extension → Azure Function App
**Browser Extension** (`Web_Extension/`)
- Captures browsing history URLs via Chrome extension
- Sends batches of URLs to Azure Function App endpoint

**Azure Function App** (`history-functions/function_app.py`)
- HTTP endpoint `/ingestHistory` receives URL batches from extension
- Saves incoming URLs to Azure Blob Storage in `pending/` folder as timestamped JSON files

### 2. Cron Job Processor
**Scheduled Processing** (`history-functions/cron_processor.py`)
- Runs periodically to get URLs form Azure Blob Storage
- Processes each batch through the scraping pipeline
- Moves processed files to `processed/` folder (or `failed/` on errors)

### 3. Scraping Pipeline
**Content Extraction** (`Tools/scraping_pipeline.py`, `Tools/robust_scraper.py`)
- Extracts product information (title, price, brand, color, category)
- Downloads representative product image from page
- Classifies as product/non-product (products only proceed to next step)

### 4. Embedding & Vector DB Upload
**Azure AI Search Ingestion** (`Tools/json2vectordb.py`)
- **Text Embedding**: Uses OpenAI `text-embedding-3-small` to embed product text
- **Image Embedding**: Uses CLIP (`openai/clip-vit-base-patch32`) to embed product images
- Uploads documents with both text and image vectors to Azure AI Search
- Enables hybrid vector + semantic search on products

### 5. AI Agent
**LangChain Agent** (`agent.py`)
- Powered by GPT-4o-mini with two tools:
  - `product_search`: Vector search on Azure AI Search (text vectors, image vectors, semantic reranking)
  - `user_preferences`: Loads computed shopping preferences from local JSON
- Prioritizes image-based matches for visual queries (color, style, appearance)

**User Preferences** (`Tools/compute_preferences.py`)
- Analyzes all indexed products to compute:
  - Top categories, brands, and colors
  - Category-specific price ranges
  - Total product count and breakdowns
- Auto-updates after each cron run with new products

### 6. Streamlit UI
**Chat Interface** (`app.py`)
- Web-based chat UI for querying the agent
- Sidebar displays user shopping profile (top categories, brands, colors, price ranges)
- Natural language queries like "Show me red sneakers" or "What's my favorite brand?"

## Setup

### Cron Job (macOS/Linux)
Run `crontab -e` and add:
```
*/10 * * * * cd /Users/aryanmehta/Desktop/History_memory/history-functions && /path/to/python3 cron_processor.py
```

### Running Locally
```bash
# Start Streamlit UI
streamlit run app.py

# Manual processing (if needed)
cd history-functions
python3 cron_processor.py
```

## Environment Variables
Set in `local.settings.json` (not committed):
- `AZURE_STORAGE_CONNECTION_STRING`
- `BLOB_CONTAINER_NAME`
- `AZURE_SEARCH_ENDPOINT`
- `AZURE_SEARCH_INDEX`
- `AZURE_SEARCH_API_KEY`
- `OPENAI_API_KEY`
