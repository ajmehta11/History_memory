import json
import re
from urllib.parse import urljoin


def get_representative_image_from_soup(soup, url):

    # STRATEGY 1: Check Open Graph meta tag (most reliable)
    og_image = soup.find('meta', property='og:image')
    if og_image and og_image.get('content'):
        print("✓ Found via Open Graph tag")
        return og_image['content']


    json_ld_scripts = soup.find_all('script', type='application/ld+json')
    for script in json_ld_scripts:
        try:
            data = json.loads(script.string)
            data_list = data if isinstance(data, list) else [data]

            for item in data_list:
                if item.get('@type') == 'Product' and 'image' in item:
                    image = item['image']
                    if isinstance(image, str):
                        print("✓ Found via Schema.org Product data")
                        return image
                    elif isinstance(image, list) and len(image) > 0:
                        print("✓ Found via Schema.org Product data")
                        return image[0] if isinstance(image[0], str) else image[0].get('url')
                    elif isinstance(image, dict) and image.get('url'):
                        print("✓ Found via Schema.org Product data")
                        return image['url']
        except (json.JSONDecodeError, AttributeError, TypeError):
            continue

    # STRATEGY 3: Score all images with heuristics
    print("✓ Using heuristic scoring...")
    images = soup.find_all('img')

    scored_images = []

    for img in images:
        # Get src (or data-src for lazy loaded images)
        src = (img.get('src') or img.get('data-src') or img.get('data-lazy-src') or
               img.get('data-srcset') or img.get('data-original'))

        if not src or src.startswith('data:'):
            continue

        # Handle srcset - take first URL
        if ',' in str(src):
            src = src.split(',')[0].split()[0]

        # Make URL absolute if relative
        if src.startswith('//'):
            src = 'https:' + src
        elif src.startswith('/'):
            src = urljoin(url, src)

        score = 0

        # Get image attributes
        width = img.get('width')
        height = img.get('height')
        alt = img.get('alt', '')
        class_str = ' '.join(img.get('class', []))

        # Try to parse dimensions
        try:
            width = int(width) if width else 0
            height = int(height) if height else 0
        except (ValueError, TypeError):
            width = 0
            height = 0

        # Skip tiny images
        if width and height and (width < 100 or height < 100):
            continue

        # SCORING FACTORS
        if width and height:
            area = width * height
            score += min(area / 10000, 100)
        else:
            score += 20

        if width and height:
            ratio = width / height if height > 0 else 0
            if 0.5 < ratio < 2.5:
                score += 30

        if len(alt) > 10:
            score += min(len(alt) / 2, 30)

        good_class_patterns = ['product', 'hero', 'main', 'feature', 'gallery', 'zoom', 'primary']
        if any(pattern in class_str.lower() for pattern in good_class_patterns):
            score += 50

        junk_class_patterns = ['logo', 'icon', 'sprite', 'banner', 'ad', 'social',
                              'avatar', 'thumb', 'badge', 'button', 'nav']
        if any(pattern in class_str.lower() for pattern in junk_class_patterns):
            score -= 50

        lower_src = src.lower()
        junk_url_patterns = ['logo', 'icon', 'sprite', 'banner', 'ad', 'social',
                           'avatar', 'badge', 'button', 'arrow', 'placeholder',
                           'transparent-pixel', 'grey-pixel', 'gray-pixel',
                           'spacer', 'loading', '1x1']
        if any(pattern in lower_src for pattern in junk_url_patterns):
            score -= 50

        good_url_patterns = ['product', 'hero', 'main', 'feature', 'gallery', 'zoom', 'item']
        if any(pattern in lower_src for pattern in good_url_patterns):
            score += 40

        # Check parent elements
        for parent in img.parents:
            if parent.name:
                parent_class = ' '.join(parent.get('class', []))
                parent_id = parent.get('id', '')

                if any(x in parent_class.lower() or x in parent_id.lower()
                      for x in ['product', 'main', 'content', 'gallery', 'detail']):
                    score += 30
                    break

        scored_images.append({
            'src': src,
            'score': score,
            'width': width,
            'height': height,
            'alt': alt[:50],
        })

    if scored_images:
        scored_images.sort(key=lambda x: x['score'], reverse=True)

        print("\nTop 3 candidates:")
        for i, img in enumerate(scored_images[:3], 1):
            print(f"{i}. Score: {img['score']:.1f} | {img['width']}x{img['height']} | {img['alt']}")
            print(f"   {img['src'][:100]}")

        return scored_images[0]['src']

    return None


def scrape_with_cloudscraper(url):
    """
    Strategy 1: Use cloudscraper (bypasses Cloudflare and most anti-bot systems)
    """
    try:
        import cloudscraper
        from bs4 import BeautifulSoup

        print("\n[Strategy 1] Trying cloudscraper...")

        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'darwin',
                'desktop': True
            }
        )

        response = scraper.get(url, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        print("✓ Successfully fetched with cloudscraper")

        return soup

    except ImportError:
        print("✗ cloudscraper not installed. Install with: pip install cloudscraper")
        return None
    except Exception as e:
        print(f"✗ cloudscraper failed: {e}")
        return None


def scrape_with_playwright(url):
    """
    Strategy 2: Use Playwright with stealth (best bot detection avoidance)
    """
    try:
        from playwright.sync_api import sync_playwright
        from bs4 import BeautifulSoup
        import time

        print("\n[Strategy 2] Trying Playwright with stealth...")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )

            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )

            # Add stealth scripts
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            page = context.new_page()
            page.goto(url, wait_until='networkidle', timeout=30000)

            # Wait for images to load
            time.sleep(2)

            html = page.content()
            browser.close()

            soup = BeautifulSoup(html, 'html.parser')
            print("✓ Successfully fetched with Playwright")

            return soup

    except ImportError:
        print("✗ Playwright not installed. Install with: pip install playwright && playwright install chromium")
        return None
    except Exception as e:
        print(f"✗ Playwright failed: {e}")
        return None


def scrape_with_selenium(url):
    """
    Strategy 3: Selenium fallback (last resort)
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from bs4 import BeautifulSoup
        import time

        print("\n[Strategy 3] Trying Selenium...")

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        driver = webdriver.Chrome(options=options)
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        driver.get(url)
        time.sleep(3)

        html = driver.page_source
        driver.quit()

        soup = BeautifulSoup(html, 'html.parser')
        print("✓ Successfully fetched with Selenium")

        return soup

    except ImportError:
        print("✗ Selenium not installed. Install with: pip install selenium")
        return None
    except Exception as e:
        print(f"✗ Selenium failed: {e}")
        return None


def get_all_images_from_soup(soup, url):
    """
    Extract all images from soup
    """
    images = soup.find_all('img')
    image_urls = []

    for img in images:
        src = (img.get('src') or img.get('data-src') or img.get('data-lazy-src') or
               img.get('data-srcset') or img.get('data-original'))

        if src and not src.startswith('data:'):
            # Handle srcset
            if ',' in str(src):
                src = src.split(',')[0].split()[0]

            # Make URL absolute
            if src.startswith('//'):
                src = 'https:' + src
            elif src.startswith('/'):
                src = urljoin(url, src)

            alt = img.get('alt', '')
            image_urls.append({'url': src, 'alt': alt})

    return image_urls


def extract_text_from_soup(soup, url):
    """
    Extract text content from the page
    """
    text_data = {}

    # Extract title
    title = soup.find('title')
    text_data['title'] = title.get_text(strip=True) if title else None

    # Extract meta description
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if not meta_desc:
        meta_desc = soup.find('meta', property='og:description')
    text_data['description'] = meta_desc.get('content', '').strip() if meta_desc else None

    # Extract main heading
    h1 = soup.find('h1')
    text_data['heading'] = h1.get_text(strip=True) if h1 else None

    # Extract main content
    # Try to find main content areas
    main_content = None
    for selector in [
        soup.find('main'),
        soup.find('article'),
        soup.find('div', class_=re.compile(r'(content|main|article|product|detail)', re.I)),
        soup.find('div', id=re.compile(r'(content|main|article|product|detail)', re.I))
    ]:
        if selector:
            main_content = selector
            break

    if not main_content:
        main_content = soup.find('body')

    # Extract paragraphs from main content
    if main_content:
        # Remove script and style elements
        for script in main_content(['script', 'style', 'nav', 'footer', 'header']):
            script.decompose()

        # Get text
        text = main_content.get_text(separator=' ', strip=True)
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text_data['main_content'] = text[:5000]  # Limit to first 5000 chars
    else:
        text_data['main_content'] = None

    # Extract all headings
    headings = []
    for i in range(1, 7):
        for heading in soup.find_all(f'h{i}'):
            heading_text = heading.get_text(strip=True)
            if heading_text:
                headings.append({'level': i, 'text': heading_text})
    text_data['headings'] = headings[:20]  # Limit to first 20 headings

    # Extract price if it's a product page
    price = None
    price_selectors = [
        soup.find('meta', property='og:price:amount'),
        soup.find(class_=re.compile(r'price', re.I)),
        soup.find('span', class_=re.compile(r'price', re.I)),
    ]

    for selector in price_selectors:
        if selector:
            if selector.name == 'meta':
                price = selector.get('content', '')
            else:
                price = selector.get_text(strip=True)
            if price:
                break

    text_data['price'] = price

    return text_data


def robust_scrape(url):
    """
    Main function: tries multiple strategies until one works
    """
    print(f"🔍 Scraping: {url}\n")
    print("=" * 80)

    soup = None

    # Try cloudscraper first (fastest, bypasses most protection)
    soup = scrape_with_cloudscraper(url)

    # Try Playwright if cloudscraper failed (most reliable)
    if soup is None:
        soup = scrape_with_playwright(url)

    # Try Selenium as last resort
    if soup is None:
        soup = scrape_with_selenium(url)

    if soup is None:
        print("\n❌ All scraping strategies failed!")
        return None, None, None

    # Extract all images
    all_images = get_all_images_from_soup(soup, url)

    print("\n=== ALL IMAGES FOUND ===\n")
    for idx, img in enumerate(all_images, 1):
        print(f"{idx}. {img['url']}")
        if img['alt']:
            print(f"   Alt: {img['alt'][:80]}")

    print(f"\n--- Total images found: {len(all_images)} ---")

    # Find representative image
    print("\n" + "=" * 80)
    print("=== FINDING REPRESENTATIVE IMAGE ===\n")

    main_image = get_representative_image_from_soup(soup, url)

    # Extract text content
    print("\n" + "=" * 80)
    print("=== EXTRACTING TEXT CONTENT ===\n")

    text_data = extract_text_from_soup(soup, url)

    return main_image, all_images, text_data


if __name__ == "__main__":
    # Test URLs
    test_url = "https://www.amazon.com/Nike-Women-Basketball-White-Green/dp/B08QBPQ1X8/?_encoding=UTF8&pd_rd_w=ygWHB&content-id=amzn1.sym.8ffe59e6-d190-4113-9581-0d24297bcb03&pf_rd_p=8ffe59e6-d190-4113-9581-0d24297bcb03&pf_rd_r=886DZE5ZP5ZSA0XHCH68&pd_rd_wg=9Nd3b&pd_rd_r=6ea9659c-7c8d-4d5e-8db8-e2d1138b4743&ref_=pd_hp_d_btf_fabric_btf_prism_premfashion_c"

    main_image, all_images, text_data = robust_scrape(test_url)

    if main_image:
        print("\n" + "=" * 80)
        print(f"🎯 REPRESENTATIVE IMAGE:\n{main_image}")
    else:
        print("\n❌ No suitable image found")

    if text_data:
        print("\n" + "=" * 80)
        print("📝 EXTRACTED TEXT CONTENT:")
        print("=" * 80)
        print(f"\nTitle: {text_data.get('title', 'N/A')}")
        print(f"\nHeading: {text_data.get('heading', 'N/A')}")
        print(f"\nDescription: {text_data.get('description', 'N/A')}")
        print(f"\nPrice: {text_data.get('price', 'N/A')}")

        if text_data.get('headings'):
            print(f"\nHeadings ({len(text_data['headings'])} found):")
            for h in text_data['headings'][:5]:
                print(f"  H{h['level']}: {h['text']}")

        if text_data.get('main_content'):
            print(f"\nMain Content (first 500 chars):")
            print(f"{text_data['main_content'][:500]}...")
    else:
        print("\n❌ No text content extracted")