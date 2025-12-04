#!/usr/bin/env python3
"""
Process browser history and extract images + text from each URL
"""

import json
import sys
from pathlib import Path

# Add Tools directory to path
sys.path.insert(0, str(Path(__file__).parent / 'Tools'))

from Tools.robust_scraper import robust_scrape


def process_history(history_file='history.json', output_file='scraped_data.json'):
    """Process all URLs from history and extract data"""

    # Load history
    with open(history_file, 'r') as f:
        history = json.load(f)

    print(f"Found {len(history)} URLs in history\n")

    results = []

    for idx, item in enumerate(history, 1):
        url = item.get('url')
        title = item.get('title', 'No title')

        print(f"\n{'='*100}")
        print(f"[{idx}/{len(history)}] Processing: {title}")
        print(f"URL: {url}")
        print('='*100)

        try:
            main_image, all_images, text_data = robust_scrape(url)

            result = {
                'url': url,
                'original_title': title,
                'lastVisitTime': item.get('lastVisitTime'),
                'visitCount': item.get('visitCount'),
                'scraped_data': {
                    'representative_image': main_image,
                    'image_count': len(all_images) if all_images else 0,
                    'text': text_data
                },
                'success': True
            }

            results.append(result)

            print(f"\n✓ Successfully scraped")
            print(f"  - Image: {main_image[:100] if main_image else 'None'}...")
            print(f"  - Title: {text_data.get('title', 'N/A') if text_data else 'N/A'}")

        except Exception as e:
            print(f"\n✗ Failed: {e}")
            results.append({
                'url': url,
                'original_title': title,
                'success': False,
                'error': str(e)
            })

        # Save after each URL (in case of crashes)
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

    print(f"\n\n{'='*100}")
    print(f"✓ Completed! Results saved to: {output_file}")
    print(f"  - Total processed: {len(results)}")
    print(f"  - Successful: {sum(1 for r in results if r.get('success'))}")
    print(f"  - Failed: {sum(1 for r in results if not r.get('success'))}")
    print('='*100)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Process browser history URLs')
    parser.add_argument('--input', default='history.json', help='Input history JSON file')
    parser.add_argument('--output', default='scraped_data.json', help='Output file for scraped data')
    parser.add_argument('--limit', type=int, help='Limit number of URLs to process')

    args = parser.parse_args()

    process_history(args.input, args.output)
