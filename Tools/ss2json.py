import json
import re
from pathlib import Path

import pytesseract
from PIL import Image

from openai import OpenAI

client = OpenAI()

def ocr_image(image_path: str) -> str:
    import os
    import subprocess

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Screenshot not found: {image_path}")

    try:
        result = subprocess.run(
            ['/opt/homebrew/bin/tesseract', image_path, 'stdout'],
            capture_output=True,
            text=False, 
            check=False,
            timeout=30
        )

        stdout_text = result.stdout.decode('utf-8', errors='replace') if result.stdout else ''

        if result.returncode != 0:
            stderr_text = result.stderr.decode('utf-8', errors='replace') if result.stderr else ''
            print(f"Tesseract error (code {result.returncode}): {stderr_text[:500]}")

            if stdout_text.strip():
                print("Using partial OCR output despite errors")
                return stdout_text

            raise Exception(f"Tesseract failed: {stderr_text[:200]}")

        return stdout_text

    except subprocess.TimeoutExpired:
        raise Exception(f"Tesseract timed out on {image_path}")
    except Exception as e:
        print(f"OCR error: {e}")
        raise


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
"""


def call_llm_for_json(ocr_text: str) -> dict:
    """
    Uses OpenAI gpt-4o-mini with enforced JSON output.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"OCR_TEXT:\n{ocr_text}\n\nReturn JSON now:"}
        ]
    )

    # Extract the JSON string
    json_str = response.choices[0].message.content
    return json.loads(json_str)



def extract_product_from_image(image_path: str) -> dict:
    ocr_text = ocr_image(image_path)

    print("OCR TEXT (debug):")
    print(ocr_text)
    print("-" * 60)

    product_info = call_llm_for_json(ocr_text)

    print("EXTRACTED JSON:")
    print(json.dumps(product_info, indent=2, ensure_ascii=False))
    return product_info


if __name__ == "__main__":
    img_path = "/Users/aryanmehta/Desktop/History_memory/screenshots/46_www.nike.com_u_nike-dunk-low-unlocked-by-you-10001638_5729010199.png"
    if not Path(img_path).exists():
        raise FileNotFoundError(f"{img_path} not found, please update the path.")
    extract_product_from_image(img_path)
