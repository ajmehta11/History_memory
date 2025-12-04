#!/usr/bin/env python3
"""
Stealth screenshot script using undetected-chromedriver
Bypasses bot detection and captcha pages
"""

import undetected_chromedriver as uc
import sys
import time


def take_screenshot(url, output_file='screenshot.png'):
    """Take a screenshot of a website with stealth mode"""

    # Configure undetected Chrome options
    options = uc.ChromeOptions()

    # Set window size (don't use headless as it's more detectable)
    options.add_argument('--window-size=1920,1080')

    # Additional stealth arguments
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')

    # Suppress logging
    options.add_argument('--log-level=3')
    options.add_argument('--silent')

    # Create undetected Chrome driver
    driver = uc.Chrome(options=options, use_subprocess=True)

    try:
        print(f"Loading: {url}")
        driver.get(url)

        # Wait for page to load and dynamic content
        print("Waiting for page to load...")
        time.sleep(5)  # Longer wait for better content loading

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

    return output_file


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Use default URL for testing
        url = "https://www.amazon.com/New-Balance-Arishi-Running-Metallic/dp/B09H3NJL37/ref=sr_1_7?adgrpid=186510817637&dib=eyJ2IjoiMSJ9.nMgWXMrq-Asl-ZL1MIcRdA9rXnSwpspxTNtm_NqTCl-1DrrWPS6X7S-mcck2vx9N7XCWIBe5bIyxF-_XebPlBcx6J3DyaKUPae6q5HG3aJwecA-CliUywquLEaZdwty9cVTfEBNpl0An-YrApAqtg3r4hE7TredMJUqbb_xukcNgo59_9CaVRBvG-xlgNk1zpL1Lsh-pphRDSv1XdlCW1JHHGy7ifEapPxcUhPR7J6Vmexkmw6-wiLqEGrSx1_Z597Bl6F0zlgvpcbC16fG6aEY3eo3e3sWPj3IR4_uIJLg.UYlpl2U-iy3oELm5PPkeU4VNiAEPLRk6SML9nbf6QJ8&dib_tag=se&hvadid=779671614866&hvdev=c&hvexpln=0&hvlocphy=9194732&hvnetw=g&hvocijid=1765297643526592377--&hvqmt=e&hvrand=1765297643526592377&hvtargid=kwd-334882149791&hydadcr=7497_13535778_2063795&keywords=newbalance%2Bamazon&mcid=88fd590c8b0e364aaa1f8e560e5a79d8&qid=1764864010&sr=8-7&th=1&psc=1"
        print("No URL specified, using default Amazon URL for testing")
    else:
        url = sys.argv[1]

    output_file = sys.argv[2] if len(sys.argv) > 2 else 'screenshot.png'

    take_screenshot(url, output_file)
