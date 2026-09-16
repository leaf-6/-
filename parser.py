#页面 → 数据

import re
from playwright.sync_api import Page

def clean_people_num(text):
    if not text:
        return 0
    nums = re.findall(r"\d+", text)
    return int(nums[0]) if nums else 0


def parse_books_from_page(page: Page):
    """从搜索页解析图书列表"""
    books = []
    items = page.locator("div.item-root")
    count = items.count()

    for i in range(count):
        item = items.nth(i)

        title_el = item.locator("a.title-text")
        if not title_el.count():
            continue

        book_url = title_el.get_attribute("href")
        if book_url and book_url.startswith("/"):
            book_url = "https://book.douban.com" + book_url

        title = title_el.inner_text().strip()

        rating_el = item.locator("span.rating_nums")
        rating_txt = rating_el.inner_text().strip() if rating_el.count() else "0.0"
        rating = float(rating_txt) if rating_txt else 0.0

        people_el = item.locator("span.pl")
        people = clean_people_num(people_el.inner_text()) if people_el.count() else 0

        meta_el = item.locator("div.meta.abstract")
        meta_text = meta_el.inner_text().strip() if meta_el.count() else ""
        parts = [p.strip() for p in meta_text.split("/") if p.strip()]

        author = parts[0] if parts else "暂无"
        pub = " / ".join(parts[-3:]) if len(parts) >= 3 else "暂无"

        books.append([title, rating, people, author, pub, book_url])

    return books


def parse_book_detail(page: Page, book_url: str):
    """解析图书详情页"""
    page.goto(book_url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_selector("#info", timeout=10000)

    page_num, isbn = "", ""

    info_spans = page.locator("#info span.pl")
    count = info_spans.count()
    for i in range(count):
        text = info_spans.nth(i).inner_text().strip()
        value = info_spans.nth(i).evaluate("""
            el => {
                let n = el.nextSibling;
                while (n) {
                    const t = (n.textContent || '').trim();
                    if (t) return t;
                    n = n.nextSibling;
                }
                return '';
            }
        """)
        if ("页" in text or "页数" in text) and not page_num:
            nums = re.findall(r"\d+", value)
            if nums:
                page_num = nums[0]
        if "ISBN" in text and not isbn:
            nums = re.findall(r"\d{10,13}", value)
            if nums:
                isbn = nums[0]

    if not isbn:
        info_all = page.locator("#info").inner_text()
        m = re.search(r"ISBN[：:\s]*([\d\-xX]{10,17})", info_all)
        if m:
            isbn = re.sub(r"[^\dXx]", "", m.group(1))

    intro = ""
    for sel in ["#link-report-intro", "#link-report .intro", "div.intro"]:
        intro_el = page.locator(sel).first
        if intro_el.count() and intro_el.inner_text().strip():
            intro = intro_el.inner_text().strip()[:200]
            break

    return {
        "pages": page_num,
        "isbn": isbn,
        "intro": intro
    }