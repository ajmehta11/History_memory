import os
import json

from langchain.tools import tool
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import VectorizedQuery

import torch
from transformers import CLIPModel, CLIPProcessor
from openai import OpenAI  


ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
INDEX = os.environ["AZURE_SEARCH_INDEX"]
API_KEY = os.environ["AZURE_SEARCH_API_KEY"]

search_client = SearchClient(
    endpoint=ENDPOINT,
    index_name=INDEX,
    credential=AzureKeyCredential(API_KEY),
)

openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

def text_embed(text: str) -> list[float]:
    """Get text embedding using the same OpenAI model as indexing."""
    resp = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return resp.data[0].embedding  


clip_model_name = "openai/clip-vit-base-patch32"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

clip_model = CLIPModel.from_pretrained(clip_model_name).to(DEVICE)
clip_processor = CLIPProcessor.from_pretrained(clip_model_name)


def clip_text_embed(text: str) -> list[float]:
    inputs = clip_processor(
        text=[text],
        images=None,
        return_tensors="pt",
        padding=True,
        truncation=True,
    ).to(DEVICE)

    with torch.no_grad():
        text_features = clip_model.get_text_features(**inputs)

    text_features = text_features / text_features.norm(p=2, dim=-1, keepdim=True)
    return text_features[0].cpu().tolist()


@tool
def product_search(query: str) -> str:
    """
    Retrieve products using Azure AI Search:

    - 20 text-vector matches (text-embedding-3-small on `text_vector`)
    - Semantic search (top 10) for reranked text docs
    - 5 image-vector matches (CLIP text → `image_vector`)

    Returns a JSON string with `text_hits` and `image_hits`.
    """

    text_vec = text_embed(query)  
    text_vector_query = VectorizedQuery(
        vector=text_vec,
        k_nearest_neighbors=20,
        fields="text_vector",
    )

    text_results = search_client.search(
        search_text=None,
        vector_queries=[text_vector_query],
        top=20,
    )

    semantic_results = search_client.search(
        search_text=query,
        query_type="semantic",
        semantic_configuration_name="products-semantic-config",
        top=10,
    )

    image_vec = clip_text_embed(query) 
    image_vector_query = VectorizedQuery(
        vector=image_vec,
        k_nearest_neighbors=5,
        fields="image_vector",
    )

    image_results = search_client.search(
        search_text=None,
        vector_queries=[image_vector_query],
        top=5,
    )

    text_hits = [
        {
            "id": d["id"],
            "content": d.get("content"),
            "product": d.get("product_json"),
        }
        for d in semantic_results
    ]

    image_hits = [
        {
            "id": d["id"],
            "content": d.get("content"),
            "product": d.get("product_json"),
        }
        for d in image_results
    ]

    return json.dumps(
        {
            "text_hits": text_hits,
            "image_hits": image_hits,
        },
        ensure_ascii=False,
    )


llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
)

agent = create_agent(
    model=llm,
    tools=[product_search],
    system_prompt=(
        "You are a helpful shopping assistant. Do not chat like a bot, chat like a human working in a shop. "
        "Use the `product_search` tool to find products, then summarize the results. For every product displayed, include the URL to the product. Also include all other available metadata like product name, price, etc.."
    ),
)


if __name__ == "__main__":
    print("Agent ready! Type 'exit' to quit.")
    while True:
        q = input("You: ").strip()
        if q.lower() in ("exit", "quit"):
            break

        result = agent.invoke(
            {"messages": [{"role": "user", "content": q}]}
        )

        final_answer = result["messages"][-1].content
        print("Agent:", final_answer)
