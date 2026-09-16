# main.py

import time
import random
from playwright.sync_api import sync_playwright
from config import STATE_FILE, USER_AGENT, KEYWORDS
from spider import scrape_keyword
from excel import save_excel

def check_login(page):
    page.goto("https://book.douban.com/", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    return "accounts.douban.com" not in page.url

def main():
    all_books = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            storage_state=STATE_FILE,
            user_agent=USER_AGENT
        )
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
        page = context.new_page()

        if not check_login(page):
            raise SystemExit("登录态失效，请重新登录")

        for kw in KEYWORDS:
            books = scrape_keyword(page, kw)
            all_books[kw] = books

            time.sleep(random.uniform(5, 8))

        browser.close()

    save_excel(all_books)

if __name__ == "__main__":
    main()