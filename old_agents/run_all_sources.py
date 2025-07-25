import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
from scripts.download_beauhurst import scrape_and_download_beauhurst
from scripts.download_pitchbook import scrape_and_download_pitchbook
from scripts.download_crunchbase import scrape_and_download_crunchbase
from playwright.sync_api import sync_playwright
from core.download_utils import NAV_TIMEOUT

if __name__ == "__main__":
    with sync_playwright() as pw:
        # Beauhurst
        print("\n--- Running Beauhurst workflow ---")
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.set_default_navigation_timeout(NAV_TIMEOUT)
        scrape_and_download_beauhurst(page)
        browser.close()

        # PitchBook
        print("\n--- Running PitchBook workflow ---")
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.set_default_navigation_timeout(NAV_TIMEOUT)
        scrape_and_download_pitchbook(page)
        browser.close()

        # Crunchbase
        print("\n--- Running Crunchbase workflow ---")
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.set_default_navigation_timeout(NAV_TIMEOUT)
        scrape_and_download_crunchbase(page)
        browser.close()

    print("\nAll sources processed.") 