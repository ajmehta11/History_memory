import json
import os
import re
from io import BytesIO

import requests
from PIL import Image
import uuid

from openai import OpenAI
from transformers import CLIPProcessor, CLIPModel
import torch

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient



AZURE_SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
AZURE_SEARCH_INDEX = os.environ["AZURE_SEARCH_INDEX"]
AZURE_SEARCH_ADMIN_KEY = os.environ["AZURE_SEARCH_ADMIN_KEY"]

openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

clip_model_name = "openai/clip-vit-base-patch32"
clip_model = CLIPModel.from_pretrained(clip_model_name)
clip_processor = CLIPProcessor.from_pretrained(clip_model_name)

device = "cuda" if torch.cuda.is_available() else "cpu"
clip_model = clip_model.to(device)

search_client = SearchClient(
    endpoint=AZURE_SEARCH_ENDPOINT,
    index_name=AZURE_SEARCH_INDEX,
    credential=AzureKeyCredential(AZURE_SEARCH_ADMIN_KEY),
)



def parse_price(price_str: str) -> float | None:
    if not price_str:
        return None
    match = re.search(r'[\d,]+\.?\d*', str(price_str).replace(',', ''))
    return float(match.group()) if match else None


def parse_colors(color_str: str) -> list[str]:
    if not color_str:
        return []
    colors = re.split(r'[/,]', color_str)
    return [c.strip() for c in colors if c.strip()]



def build_text_from_product(p: dict) -> str:
    parts = []
    if p.get("product_name"):
        parts.append(f"Product name: {p['product_name']}")
    if p.get("Brand"):
        parts.append(f"Brand: {p['Brand']}")
    if p.get("Color"):
        parts.append(f"Color: {p['Color']}")
    if p.get("price"):
        parts.append(f"Price: {p['price']} {p.get('currency', '')}")
    if p.get("Category"):
        parts.append(f"Category: {p['Category']}")
    if p.get("description"):
        parts.append(f"Description: {p['description']}")
    if p.get("additional_attributes"):
        parts.append(f"Attributes: {json.dumps(p['additional_attributes'])}")
    if p.get("original_title"):
        parts.append(f"Original title: {p['original_title']}")
    return "\n".join(parts)


def embed_text(text: str) -> list[float]:
    resp = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return resp.data[0].embedding


def embed_image_from_url(url: str) -> list[float] | None:
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()

        image = Image.open(BytesIO(resp.content)).convert("RGB")

        if image.size[0] < 50 or image.size[1] < 50:
            print(f"Skipping tiny image: {image.size}")
            return None

        inputs = clip_processor(images=image, return_tensors="pt").to(device)

        with torch.no_grad():
            image_features = clip_model.get_image_features(**inputs)

        image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
        return image_features.squeeze().cpu().tolist()
    except Exception as e:
        print(f"Error embedding image: {e}")
        return None 



def ingest_product_to_azure_search(product: dict):
    content_text = build_text_from_product(product)
    text_vec = embed_text(content_text)

    img_vec = None
    if product.get("main_image"):
        img_vec = embed_image_from_url(product["main_image"])

    url = product.get("url")
    if url:
        doc_id = str(uuid.uuid5(uuid.NAMESPACE_URL, url))
    else:
        doc_id = str(uuid.uuid4())

    attrs = product.get("additional_attributes", {})

    doc = {
        "id": doc_id,
        "content": content_text,
        "product_json": json.dumps(product),
        "text_vector": text_vec,
        
        "product_name": product.get("product_name"),
        "brand": product.get("Brand"),
        "category": product.get("Category"),
        "colors": parse_colors(product.get("Color")),
        "price": parse_price(product.get("price")),
        "size": attrs.get("Size"),
        "condition": attrs.get("Condition"),
    }

    if img_vec is not None:
        doc["image_vector"] = img_vec

    result = search_client.upload_documents(documents=[doc])
    print("Upload result:", result)
    return result



def ingest_products_batch(products: list[dict]):
    total = len(products)
    successful = 0
    failed = 0

    for idx, product in enumerate(products, 1):
        print(f"\n[{idx}/{total}] Processing: {product.get('product_name', 'Unknown')}")
        try:
            ingest_product_to_azure_search(product)
            successful += 1
        except Exception as e:
            failed += 1
            print(f"✗ Error ingesting product: {e}")

    print(f"\n{'='*80}")
    print(f"Batch upload complete: {successful} successful, {failed} failed out of {total} total")
    print(f"{'='*80}")



if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Upload products from JSON file to Azure AI Search"
    )
    parser.add_argument(
        "--file",
        default="my_products.json",
        help="Path to JSON file containing products (default: my_products.json)"
    )

    args = parser.parse_args()

    print(f"Loading products from {args.file}...")
    with open(args.file, 'r') as f:
        products = json.load(f)

    print(f"Loaded {len(products)} products\n")

    ingest_products_batch(products)