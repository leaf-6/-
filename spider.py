# spider.py

import time
import random
from playwright.sync_api import Page
# from config import MAX_PAGES
from progress import load_progress, save_progress
from parser import parse_books_from_page, parse_book_detail

def scrape_keyword(page: Page, keyword: str):
    """
    爬取单个关键词
    返回：该关键词下的图书列表
    """
    prog = load_progress()
    kp = prog.get(keyword, {"page": 0, "detail_done": []})

    page_num = kp["page"]
    detail_done = set(kp["detail_done"])
    results = []

    print(f"\n[关键词: {keyword}] 从第 {page_num} 页开始")
    empty_pages = 0
    while True:
        # if page_num >= MAX_PAGES:
        #     print(" 已达到安全上限，强制停止")
        #     break

        start = page_num * 15
        url = f"https://book.douban.com/subject_search?search_text={keyword}&start={start}"
        print(f"[Page {page_num}] {url}")

        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(random.randint(1000, 2000))

        books = parse_books_from_page(page)

        if not books:
            empty_pages += 1
            print(f" 本页无书（连续 {empty_pages} 页）")
            if empty_pages >= 6:
                print(f" 连续 10 页无书，{keyword}关键词结束爬取，暂停五分钟，再下一个关键词爬取")
                time.sleep(300)
                break
        else:
            empty_pages = 0 #有书就清零

        for b in books:
            book_url = b[5]
            if not book_url or book_url in detail_done:
                b.extend(["", "", ""])
                continue

            detail = parse_book_detail(page, book_url)
            b.extend([detail["pages"], detail["isbn"], detail["intro"]])
            detail_done.add(book_url)
            time.sleep(random.uniform(3, 5))

        results.extend(books)
        print(f" 本页 {len(books)} 条，累计 {len(results)} 条")

    
        page_num += 1
        save_progress(keyword, page_num, detail_done)
        time.sleep(random.uniform(2, 4))

    results.sort(key=lambda x: x[1], reverse=True)
    return results