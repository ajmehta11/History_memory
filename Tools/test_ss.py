#!/usr/bin/env python3
"""
Take screenshots for all URLs in history.json
Uses stealth mode to bypass bot detection
"""

import json
import os
from pathlib import Path

# Try to use stealth version first, fall back to regular version
try:
    from ss_stealth import take_screenshot
    print("Using ss_stealth.py (undetected-chromedriver)")
except ImportError:
    print("Warning: undetected-chromedriver not available, falling back to enhanced Selenium")
    print("Install with: pip install undetected-chromedriver")
    from ss import take_screenshot


def create_screenshot_folder(folder_name='screenshots'):
    """Create folder for screenshots"""
    Path(folder_name).mkdir(exist_ok=True)
    return folder_name


def sanitize_filename(url, index):
    """Create a safe filename from URL"""
    # Remove protocol and special characters
    safe_name = url.replace('https://', '').replace('http://', '')
    safe_name = safe_name.replace('/', '_').replace('?', '_').replace('&', '_')

    # Limit length
    if len(safe_name) > 100:
        safe_name = safe_name[:100]

    return f"{index}_{safe_name}.png"


def process_all_urls(history_file='history.json', output_folder='screenshots', limit=None):
    """Take screenshots for all URLs in history"""

    # Load history
    with open(history_file, 'r') as f:
        history = json.load(f)

    # Create output folder
    folder = create_screenshot_folder(output_folder)

    # Limit if specified
    urls_to_process = history[:limit] if limit else history

    print(f"Processing {len(urls_to_process)} URLs from history")
    print(f"Saving screenshots to: {folder}/\n")

    results = []

    for idx, item in enumerate(urls_to_process, 1):
        url = item.get('url')
        title = item.get('title', 'No title')

        print(f"\n{'='*100}")
        print(f"[{idx}/{len(urls_to_process)}] {title}")
        print(f"URL: {url}")
        print('='*100)

        # Create filename
        filename = sanitize_filename(url, idx)
        output_path = os.path.join(folder, filename)

        try:
            take_screenshot(url, output_path)
            results.append({
                'index': idx,
                'url': url,
                'title': title,
                'screenshot': output_path,
                'success': True
            })
            print(f"✓ Screenshot saved: {output_path}")

        except Exception as e:
            print(f"✗ Failed: {e}")
            results.append({
                'index': idx,
                'url': url,
                'title': title,
                'success': False,
                'error': str(e)
            })

    # Save results log
    log_file = os.path.join(folder, 'screenshot_log.json')
    with open(log_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n\n{'='*100}")
    print("SUMMARY")
    print('='*100)
    print(f"Total processed: {len(results)}")
    print(f"Successful: {sum(1 for r in results if r.get('success'))}")
    print(f"Failed: {sum(1 for r in results if not r.get('success'))}")
    print(f"Screenshots saved to: {folder}/")
    print(f"Log saved to: {log_file}")
    print('='*100)

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Take screenshots of all URLs in history')
    parser.add_argument('--input', default='history.json', help='Input history JSON file')
    parser.add_argument('--output', default='screenshots', help='Output folder for screenshots')
    parser.add_argument('--limit', type=int, help='Limit number of URLs to process')

    args = parser.parse_args()

    process_all_urls(args.input, args.output, args.limit)
