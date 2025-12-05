#!/usr/bin/env python3
"""
Enhanced screenshot script using Selenium with stealth options
Fallback option if undetected-chromedriver is not available
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import sys
import time
import random


def take_screenshot(url, output_file='screenshot.png'):
    """Take a screenshot of a website with enhanced stealth"""

    options = Options()

    # Enhanced stealth arguments
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-setuid-sandbox")

    # Use headless=new (less detectable than old headless)
    options.add_argument("--headless=new")

    # Better user agent
    options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    # Suppress automation flags
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    # Suppress logging
    options.add_argument('--log-level=3')
    options.add_argument('--silent')

    driver = webdriver.Chrome(options=options)

    # Execute CDP commands to hide webdriver
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })

    # Hide webdriver property
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    try:
        print(f"Loading: {url}")
        driver.get(url)

        # Wait for page to load with random delay to mimic human behavior
        wait_time = random.uniform(3, 5)
        print(f"Waiting {wait_time:.1f}s for page to load...")
        time.sleep(wait_time)

        # Scroll to trigger lazy loading
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

        print(f"Taking screenshot...")
        driver.save_screenshot(output_file)

        print(f"✓ Screenshot saved to: {output_file}")

    except Exception as e:
        print(f"✗ Error: {e}")
        raise

    finally:
        driver.quit()


if __name__ == "__main__":
    # if len(sys.argv) < 2:
    #     print("Usage: python ss.py <url> [output_file]")
    #     print("Example: python ss.py https://example.com screenshot.png")
    #     sys.exit(1)

    url = "https://www.amazon.com/New-Balance-Arishi-Running-Metallic/dp/B09H3NJL37/ref=sr_1_7?adgrpid=186510817637&dib=eyJ2IjoiMSJ9.nMgWXMrq-Asl-ZL1MIcRdA9rXnSwpspxTNtm_NqTCl-1DrrWPS6X7S-mcck2vx9N7XCWIBe5bIyxF-_XebPlBcx6J3DyaKUPae6q5HG3aJwecA-CliUywquLEaZdwty9cVTfEBNpl0An-YrApAqtg3r4hE7TredMJUqbb_xukcNgo59_9CaVRBvG-xlgNk1zpL1Lsh-pphRDSv1XdlCW1JHHGy7ifEapPxcUhPR7J6Vmexkmw6-wiLqEGrSx1_Z597Bl6F0zlgvpcbC16fG6aEY3eo3e3sWPj3IR4_uIJLg.UYlpl2U-iy3oELm5PPkeU4VNiAEPLRk6SML9nbf6QJ8&dib_tag=se&hvadid=779671614866&hvdev=c&hvexpln=0&hvlocphy=9194732&hvnetw=g&hvocijid=1765297643526592377--&hvqmt=e&hvrand=1765297643526592377&hvtargid=kwd-334882149791&hydadcr=7497_13535778_2063795&keywords=newbalance%2Bamazon&mcid=88fd590c8b0e364aaa1f8e560e5a79d8&qid=1764864010&sr=8-7&th=1&psc=1"
    output_file = 'screenshot.png'

    take_screenshot(url, output_file)
