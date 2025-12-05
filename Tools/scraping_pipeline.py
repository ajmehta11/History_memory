import json
import os
import uuid
from pathlib import Path
from openai import OpenAI

from robust_scraper import robust_scrape
from ss import take_screenshot
from ss2json import ocr_image, JSON_SCHEMA_EXAMPLE

client = OpenAI()


SMART_SYSTEM_PROMPT = f"""
You are a robust product-information extraction engine.

You will receive TWO inputs:
1. OCR_TEXT = noisy, possibly incomplete screenshot OCR
2. SCRAPED_TEXT = clean structured text extracted from HTML

Rules:
- Use OCR_TEXT **only if** it contains clear product information.
- If OCR_TEXT is noisy, missing price/name/brand/color/etc., rely on SCRAPED_TEXT.
- Never ask for more info.
- Produce ONE final JSON object following EXACTLY this schema:

{json.dumps(JSON_SCHEMA_EXAMPLE, indent=2)}

Additional rules:
- If a field is missing in BOTH OCR and SCRAPED TEXT, set it to null.
- Never invent unrealistic attributes.
- Output MUST be a valid JSON object and nothing else.
"""


def call_llm_smart(ocr_text: str, scraped_text: dict) -> dict:

    dumped_scraped_text = json.dumps(scraped_text, indent=2, ensure_ascii=False)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SMART_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "OCR_TEXT:\n"
                    + ocr_text[:5000]
                    + "\n\nSCRAPED_TEXT:\n"
                    + dumped_scraped_text
                    + "\n\nReturn ONE final JSON now:"
                )
            }
        ]
    )

    json_str = response.choices[0].message.content
    return json.loads(json_str)


def scrape_to_json(url: str, output_dir="output", last_visit_time=None):
    Path(output_dir).mkdir(exist_ok=True)

    # Ensure URL has a protocol
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
        print(f"Added protocol to URL: {url}")

    print("\n==== STEP 1: Robust Scraping ====\n")
    main_image, all_images, text_data = robust_scrape(url)

    print("\n==== STEP 2: Screenshot Capture ====\n")
    screenshot_file = f"{output_dir}/{uuid.uuid4().hex}_screenshot.png"
    take_screenshot(url, screenshot_file)

    print("\n==== STEP 3: OCR on Screenshot ====\n")
    ocr_text = ocr_image(screenshot_file)

    print("\n==== STEP 4: LLM JSON Extraction (OCR + scraped text fallback) ====\n")
    final_json = call_llm_smart(ocr_text, text_data)

    enriched_json = {
        **final_json,
        "url": url,
        "lastVisitTime": last_visit_time,
        "original_title": text_data.get("title"),
        "main_image": main_image,
    }

    print("\nFINAL JSON OUTPUT:\n")
    print(json.dumps(enriched_json, indent=2, ensure_ascii=False))

    out_json_path = f"{output_dir}/{uuid.uuid4().hex}_product.json"
    with open(out_json_path, "w") as f:
        json.dump(enriched_json, f, indent=2, ensure_ascii=False)

    print(f"\nSaved JSON → {out_json_path}")
    print(f"Saved screenshot → {screenshot_file}")
    print(f"Representative image → {main_image}")

    return enriched_json



if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scrape website → screenshot → OCR → JSON pipeline")
    parser.add_argument("url", help="URL of website to scrape")
    parser.add_argument("--out", default="output", help="Output directory")

    args = parser.parse_args()
    scrape_to_json(args.url, args.out)
