import json
import os
from io import BytesIO

import requests
from PIL import Image
import uuid

from openai import OpenAI
from transformers import CLIPProcessor, CLIPModel
import torch

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient


#CONFIG 

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


#  EMBEDDING  

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
    # if p.get("url"):
    #     parts.append(f"URL: {p['url']}")
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
    except Exception:
        return None

    image = Image.open(BytesIO(resp.content)).convert("RGB")
    inputs = clip_processor(images=image, return_tensors="pt").to(device)

    with torch.no_grad():
        image_features = clip_model.get_image_features(**inputs)

    image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
    return image_features.squeeze().cpu().tolist() 


#  MAIN FUNCTION 

def ingest_product_to_azure_search(product: dict):
    content_text = build_text_from_product(product)

    text_vec = embed_text(content_text)

    img_vec = None
    if product.get("main_image"):
        img_vec = embed_image_from_url(product["main_image"])

    doc_id = product.get("url") or product.get("product_name")

    doc = {
        "id": str(uuid.uuid4()),
        "content": content_text,
        "product_json": json.dumps(product),   
        "text_vector": text_vec,
    }

    if img_vec is not None:
        doc["image_vector"] = img_vec

    result = search_client.upload_documents(documents=[doc])
    print("Upload result:", result)


#  EXAMPLE 

if __name__ == "__main__":
    sample_product = {
  "is_product": "Yes",
  "product_name": "Argentina 25/26 Home Jersey Messi Alvarez Martinez S-4XL",
  "Color": None,
  "Brand": None,
  "price": "US $45.00",
  "currency": "USD",
  "rating": None,
  "rating_count": None,
  "description": "• Sizes: Small–4XL.",
  "Category": "Clothing",
  "additional_attributes": {
    "Size": "S-4XL",
    "Condition": "Used"
  },
  "url": "https://www.ebay.com/itm/406355466405?itmprp=encpd%3AAQAKAAABkNSQ2wRUFL4S6r8jpJZpLY0CfRQJHyhhEcn9%2Fh4NIa4V5l%2BioVkkTld5evG5bQNaRpLubxccssYWVBQHFqJl1kNhCcsPY7p5skWWObw76zIVqTC24aiAWOOJCtbHMkV3CSrgHECuaNrJwu49wAYl8fuulkS0wpOhWw6%2FTukDtUsVv4KEDYrgbHCE4d6m8eif9tLLRJBZByTdNHTxjZ7ZM8F90iu%2FrmKeDBt8GYRtdX1y9n%2F9dL432NdKrofyK1ZGkfYK44moJfUpdqi8T5rrGn%2B%2FSu%2Bfzmm191BwjWxHTg77mZXlNYxOkgYSijUogz9mjpWt8bAdUlybSjFdiWNNd0TjMvNQgKQY9Mwsd3FAZfkYc9zg6KoP4YMbPj%2BKmayLmctotNAsBY7gWrHSAxPubIPHqlnMsYMyiC5ZolvzlJta9ImNnKgcr8FYGxXG%2BRrDSgfCfa3%2FYUROxlD7rUlFCmXtWww0JQwdnAnB23mq6gLTWIGm6pLPaP%2BJ0mhktBuIU6FnNuj3n4EBoSAoUtR5gmA%3D&itmmeta=wwHmKhYwY%2Fjx0DQwMUtCSzhFV0hHNVBWWEIzUU4xWDY5RE5GNDQwMUtCSzhFVzlTVFI2VDdXUDRLQ1Y3UTFYQrC4DA%3D%3D",
  "lastVisitTime": None,
  "original_title": "Argentina 25/26 Home Jersey Messi Alvarez Martinez S-4XL | eBay",
  "main_image": "https://i.ebayimg.com/images/g/VPgAAeSwspRpDDah/s-l400.jpg"
}

    ingest_product_to_azure_search(sample_product)
