"""Save dashboard screenshots to docs/. Run with the dashboard up on port 8501.

Usage: make screenshots
"""
from playwright.sync_api import sync_playwright

SHOTS = {"Overview": "docs/overview.png", "Time to close": "docs/time_to_close.png", "Anomalies": "docs/anomalies.png"}


def main():
    with sync_playwright() as play:
        browser = play.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.goto("http://localhost:8501")
        page.get_by_role("tab", name="Overview").wait_for(timeout=60000)
        for tab, path in SHOTS.items():
            page.get_by_role("tab", name=tab).click()
            page.wait_for_timeout(5000)
            page.screenshot(path=path)
            print(f"saved {path}")
        browser.close()


if __name__ == "__main__":
    main()
