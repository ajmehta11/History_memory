import json
import re
from pathlib import Path

import pytesseract
from PIL import Image

from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline


# def ocr_image(image_path: str) -> str:
#     """
#     Run OCR on an ecommerce screenshot and return raw text.
#     """
#     img = Image.open(image_path)
#     text = pytesseract.image_to_string(img)
#     return text


MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.3"  # example; pick what fits your hardware

print("Loading model... (first time will be slow)")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    device_map="auto",          # uses GPU if available, else CPU
    torch_dtype="auto"
)
generator = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer
)

JSON_SCHEMA_EXAMPLE = {
    "is_product": "Yes if it the website has a product on a shopping/ecommerce/any other website, No if it is some other website eg. google search, chatgpt, blogs, etc.",
    "product_name": "string",
    "Color": "color of the product if available",
    "Brand": "brand of the product that the product belongs to",
    "price": "string (numeric value with currency symbol if present)",
    "currency": "string or null (e.g. 'USD', 'INR', 'EUR')",
    "rating": "number or null (e.g. 4.5)",
    "rating_count": "integer or null (e.g. 1234)",
    "description": "string or null",
    "Category": "Electronics, Shoes, Clothing, Mobile, Home, etc.",
    "additional_attributes": {
        "key": "value (any other useful attributes like size, color, brand, etc.)"
    }
}

SYSTEM_PROMPT = f"""
You are a data extraction engine.

You will receive raw OCR text from an e-commerce product page screenshot.
Your task is to extract product information and return ONLY valid JSON, matching this schema:

{json.dumps(JSON_SCHEMA_EXAMPLE, indent=2)}

Rules:
- If a field is missing in the text, set it to null.
- Do NOT include any explanation, markdown, or text outside the JSON.
- Do NOT add extra keys beyond the schema.
- Ensure the JSON is syntactically valid.
"""

def build_prompt(ocr_text: str) -> str:
    return (
        SYSTEM_PROMPT
        + "\n\nOCR_TEXT:\n"
        + ocr_text
        + "\n\nReturn JSON now:"
    )


def call_llm_for_json(ocr_text: str) -> dict:
    """
    Call the LLM with the OCR text and interpret the output as JSON.
    Includes a small cleanup step in case the model wraps JSON in extra text.
    """
    prompt = build_prompt(ocr_text)

    out = generator(
        prompt,
        max_new_tokens=512,
        temperature=0.2,
        do_sample=False,
        return_full_text=False,
    )[0]["generated_text"]

    # Extract JSON substring (best-effort)
    json_str = extract_json_block(out)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        print("JSON decode error:", e)
        print("Raw LLM output:\n", out)
        raise

    return data


def extract_json_block(text: str) -> str:
    """
    Extract the first {...} block from text.
    """
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Could not find JSON object in model output.")
    return text[start : end + 1]


# ------- MAIN ENTRYPOINT -------

def extract_product_from_image(image_path: str) -> dict:
    # ocr_text = ocr_image(image_path)
    ocr_text = """  
    {
    "url": "https://www.bestbuy.com/product/samsung-galaxy-s24-ultra-512gb-s928u-unlocked-titanium-orange/J3ZYG2TCR4/sku/11153991",
    "original_title": "Samsung Refurbished Excellent Galaxy S24 Ultra 512GB S928U Unlocked Titanium Orange S928U - Best Buy",
    "lastVisitTime": 1764804405908.171,
    "visitCount": 1,
    "scraped_data": {
      "representative_image": "https://pisces.bbystatic.com/image2/BestBuy_US/images/products/297d277d-b06f-4f78-a2e4-7d9bfd362658.jpg;maxHeight=1920;maxWidth=900?format=webp",
      "image_count": 6,
      "text": {
        "title": "Samsung Refurbished Excellent Galaxy S24 Ultra 512GB S928U Unlocked Titanium Orange S928U - Best Buy",
        "description": "Shop Samsung Refurbished Excellent Galaxy S24 Ultra 512GB S928U Unlocked Titanium Orange products at Best Buy. Find low everyday prices and buy online for delivery or in-store pick-up. Price Match Guarantee.",
        "heading": "Samsung - Refurbished Excellent - Galaxy S24 Ultra 512GB S928U Unlocked - Titanium Orange",
        "main_content": "",
        "headings": [
          {
            "level": 1,
            "text": "Samsung - Refurbished Excellent - Galaxy S24 Ultra 512GB S928U Unlocked - Titanium Orange"
          },
          {
            "level": 1,
            "text": "Finance Options"
          },
          {
            "level": 2,
            "text": "Color:"
          },
          {
            "level": 2,
            "text": "Compare similar products"
          },
          {
            "level": 2,
            "text": "Reviews"
          },
          {
            "level": 3,
            "text": "Features"
          },
          {
            "level": 3,
            "text": "Questions & Answers"
          },
          {
            "level": 3,
            "text": "Similar products from outside of Best Buy"
          },
          {
            "level": 5,
            "text": "Specifications"
          }
        ],
        "price": ""
      }
    }
    """
    print("OCR TEXT (debug):")
    print(ocr_text)
    print("-" * 60)

    product_info = call_llm_for_json(ocr_text)
    print("EXTRACTED JSON:")
    print(json.dumps(product_info, indent=2, ensure_ascii=False))
    return product_info


if __name__ == "__main__":
    # Replace with path to your screenshot
    img_path = "/content/9_www.bestbuy.com_product_oneplus-13r-256gb-unlocked-nebula-noir_CZYJWF7XWW.png"
    if not Path(img_path).exists():
        raise FileNotFoundError(f"{img_path} not found, please update the path.")
    extract_product_from_image(img_path)
