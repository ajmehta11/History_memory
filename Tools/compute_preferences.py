import json
import os
import statistics
from collections import Counter, defaultdict

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient


AZURE_SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
AZURE_SEARCH_INDEX = os.environ["AZURE_SEARCH_INDEX"]
AZURE_SEARCH_ADMIN_KEY = os.environ["AZURE_SEARCH_ADMIN_KEY"]

search_client = SearchClient(
    endpoint=AZURE_SEARCH_ENDPOINT,
    index_name=AZURE_SEARCH_INDEX,
    credential=AzureKeyCredential(AZURE_SEARCH_ADMIN_KEY),
)


def get_all_products():
    results = search_client.search(
        search_text="*",
        select=["product_json"],
        top=10000 
    )

    products = []
    for result in results:
        if result.get("product_json"):
            product = json.loads(result["product_json"])
            products.append(product)

    return products


def compute_preferences(products):

    category_counter = Counter()
    brand_counter = Counter()
    color_counter = Counter()

    category_data = defaultdict(lambda: {
        "products": [],
        "brands": Counter(),
        "colors": Counter(),
        "sizes": Counter(),
        "conditions": Counter(),
        "prices": []
    })

    for product in products:
        category = product.get("Category")
        brand = product.get("Brand")
        color = product.get("Color")

        if category:
            category_counter[category] += 1
        if brand:
            brand_counter[brand] += 1
        if color:
            # Handle multi-color (e.g., "Black/White")
            colors = [c.strip() for c in color.replace('/', ',').split(',')]
            for c in colors:
                if c:
                    color_counter[c] += 1

        if category:
            cat_data = category_data[category]
            cat_data["products"].append(product)

            if brand:
                cat_data["brands"][brand] += 1

            if color:
                colors = [c.strip() for c in color.replace('/', ',').split(',')]
                for c in colors:
                    if c:
                        cat_data["colors"][c] += 1

            attrs = product.get("additional_attributes", {})
            size = attrs.get("Size")
            if size:
                cat_data["sizes"][size] += 1

            condition = attrs.get("Condition")
            if condition:
                cat_data["conditions"][condition] += 1

            price_str = product.get("price")
            if price_str:
                import re
                match = re.search(r'[\d,]+\.?\d*', str(price_str).replace(',', ''))
                if match:
                    try:
                        price = float(match.group())
                        cat_data["prices"].append(price)
                    except ValueError:
                        pass

    preferences = {
        "user_id": "default_user",
        "total_products": len(products),
        "top_categories": [cat for cat, _ in category_counter.most_common(10)],
        "top_brands": [brand for brand, _ in brand_counter.most_common(10)],
        "top_colors": [color for color, _ in color_counter.most_common(10)],
        "category_preferences": {}
    }

    for category, data in category_data.items():
        cat_pref = {
            "count": len(data["products"]),
            "brands": dict(data["brands"]),
            "top_brands": [brand for brand, _ in data["brands"].most_common(3)],
            "colors": dict(data["colors"]),
            "favorite_colors": [color for color, _ in data["colors"].most_common(3)],
            "sizes": dict(data["sizes"]),
            "preferred_sizes": [size for size, _ in data["sizes"].most_common(3)],
            "conditions": dict(data["conditions"]),
            "preferred_condition": data["conditions"].most_common(1)[0][0] if data["conditions"] else None,
        }

        if data["prices"]:
            cat_pref["price_range"] = {
                "min": round(min(data["prices"]), 2),
                "max": round(max(data["prices"]), 2),
                "avg": round(statistics.mean(data["prices"]), 2),
                "median": round(statistics.median(data["prices"]), 2)
            }
        else:
            cat_pref["price_range"] = {
                "min": None,
                "max": None,
                "avg": None,
                "median": None
            }

        preferences["category_preferences"][category] = cat_pref

    return preferences


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Compute user preferences from Azure AI Search products"
    )
    parser.add_argument(
        "--output",
        default="user_preferences.json",
        help="Output file path (default: user_preferences.json)"
    )

    args = parser.parse_args()

    print("Fetching products from Azure AI Search...")
    products = get_all_products()
    print(f"Retrieved {len(products)} products\n")

    print("Computing preferences...")
    preferences = compute_preferences(products)

    print(f"\nWriting preferences to {args.output}...")
    with open(args.output, 'w') as f:
        json.dump(preferences, f, indent=2, ensure_ascii=False)

    print(f"✓ Successfully wrote preferences to {args.output}")
    print(f"\nSummary:")
    print(f"  Total products: {preferences['total_products']}")
    print(f"  Top categories: {', '.join(preferences['top_categories'][:5])}")
    print(f"  Top brands: {', '.join(preferences['top_brands'][:5])}")
    print(f"  Top colors: {', '.join(preferences['top_colors'][:5])}")
