# -*- coding: utf-8 -*-
#一个关键词的完整爬取流程
import time
import random
import re
from playwright.sync_api import sync_playwright
from openpyxl import Workbook
import json
import os

STATE_FILE = "douban_state.json"
PROGRESS_FILE = "douban_progress.json"   # with sync_playwright()断点文件

# ========== 在这里加你的关键词 ==========
KEYWORDS = [
    "自我管理",
    "时间管理",
    "GTD",
    "效率"
]

def load_progress():
    if not os.path.exists(PROGRESS_FILE):
        return {}

    with open(PROGRESS_FILE, "r",encoding='utf-8') as f:
        data = json.load(f)

    if isinstance(data,list):
        return {k:{"page":0,"detail_done":[]} for k in data}

    for k,v in data.items():
        if isinstance(v,int):
            data[k] = {"page":v,"detail_done":[]}
        elif "detail_done" not in v:
            data[k]["detail_done"] = []
    return data

def save_resume_point(keyword,page,detail_done):
    prog = load_progress()
    prog[keyword] = {
        "page":page,
        "detail_done":sorted(detail_done),
    }
    with open(PROGRESS_FILE,"w",encoding='utf-8') as f:
        #ensure_ascii=False → 中文关键词直接存成中文
        #indent=2 → 缩进 2 空格，格式化好看，方便手动查看/编辑。
        json.dump(prog,f,ensure_ascii=False,indent=2)


# 3. 人数过滤
def clean_people_num(text):
    if not text:
        return 0
    nums = re.findall(r"\d+", text)
    return int(nums[0]) if nums else 0

#2. 从页面解析图书
def parse_books_from_page(page):
    books = []
    items = page.locator("div.item-root") #locator 定位器
    count = items.count()

    for i in range(count):
        item = items.nth(i)

        title_el = item.locator("a.title-text") #title_el 标题元素
        if not title_el.count():
            continue                # 如果不存在标题，跳过该循环，进入下一个；下面的可以去默认值，所以可以不用continue
        book_url = title_el.get_attribute("href")
        if book_url and book_url.startswith("/"):
            book_url = "https://book.douban.com" + book_url
        title = title_el.inner_text().strip()


        rating_el = item.locator("span.rating_nums") #rating_el 评级元素
        rating_txt = rating_el.inner_text().strip() if rating_el.count() else "0.0"
        rating = float(rating_txt) if rating_txt else 0.0

        people_el = item.locator("span.pl") #people_el 人员要素
        people = clean_people_num(people_el.inner_text()) if people_el.count() else 0

        # if rating == 0.0 or people == 0:  # 过滤无效条目
        #     continue

        meta_el = item.locator("div.meta.abstract") #meta_el  元元素
        meta_text = meta_el.inner_text().strip() if meta_el.count() else ""
        parts = [p.strip() for p in meta_text.split("/") if p.strip()]
        author = parts[0] if parts else "暂无"
        pub = " / ".join(parts[-3:]) if len(parts) >= 3 else "暂无"

        books.append([title, rating, people, author, pub,book_url])

    return books

#解析图书详情
def parse_book_detail(page, book_url,retries =2):
    for attempt in range(retries + 1):
        try:
            page.goto(book_url,wait_until="domcontentloaded",timeout=30000)
            page.wait_for_selector("#info",timeout=10000)
            page.wait_for_timeout(random.randint(1500,2500))
            break
        except Exception as e:
            if attempt == retries:
                print(f"详情页加载失败（已达重试上限）: {e}")
                return None
            print(f" 详情页加载异常，第{attempt+1}重试")
            time.sleep(2)

    if "accounts.douban.com" in page.url or "login" in page.url.lower():
        print(f" 被重定向到登录页{page.url}, 登录态失效！")
        return None

    # 页数
    page_num ,isbn = "" ,""
    try:

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
                nums = re.findall(r"\d+",value)
                if nums:
                    page_num = nums[0]
            if "ISBN" in text and not isbn:
                nums = re.findall(r"\d{10,13}",value)
                if nums:
                    isbn = nums[0]

        if not isbn:
            info_all = page.locator("#info").inner_text()
            m = re.search(r"ISBN[：:\s]*([\d\-xX]{10,17})", info_all)  ##info 里的纯文本包含 ISBN、也可能包含其它 10~13 位数字（比如某些编号）。re.search(r"\d{10,13}") 抓到的第一个不一定真是 ISBN。re.search(r"\d{10,13}") 抓到的第一个不一定真是 ISBN。

            #  m.group(0) = 整个匹配，比如 "ISBN: 978-7-111-46123-4"
            # .group(1) 拿到的是冒号后面那串 ISBN 原始文本（可能还带连字符）

            if m:
                isbn = re.sub(r"[^\dXx]", "", m.group(1))
                # re.sub(模式, 替换成什么, 原字符串) = 把匹配到的字符替换掉。
                # ^ 表示取反，即"不是这些字符的任意字符"

    except Exception as e:
        print(f" #info 解析异常： {e}")

    # 内容简介
    intro = ""
    for sel in ["#link-report-intro","#link-report .intro","div.intro"]:
        intro_el = page.locator(sel).first
        if intro_el.count() and intro_el.inner_text().strip():
            intro = intro_el.inner_text().strip()[:200]
            break


    print(f"  → 页数={page_num}, ISBN={isbn}, 简介{len(intro)}字")


    return {
        "pages": page_num,
        "isbn": isbn,
        "intro": intro

    }



#1. 抓取关键词
def scrape_keyword(page, keyword):
    """页级断点版：从断点页开始，爬到无书为止"""
    prog = load_progress()
    kp = prog.get(keyword, {"page":0,"detail_done":[]})
    page_num = kp["page"]
    detail_done = set(kp["detail_done"])
    results = []
    # seen = set() #去重
    print(f"\n[关键词: {keyword}] 从第 {page_num} 页开始")

    while True:
        start = page_num * 15
        url = f"https://book.douban.com/subject_search?search_text={keyword}&start={start}"
        print(f"\n[关键词: {keyword}] [Page {page_num}] {url}")

        try:
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(random.randint(1000,2000))
            # 随机滑动一下鼠标
            page.mouse.move(random.randint(100,500),random.randint(100,500),steps=10)
            page.wait_for_timeout(random.randint(1000,2000))

        except Exception as e:
            print(f" 请求失败: {e}")
            break

        books = parse_books_from_page(page)

        for b in books:
            book_url = b[5]
            if not book_url:
                b.extend(["","",""])
                continue
            if book_url in detail_done:
                print(f"详情页已存，跳过:{book_url}")
                b.extend(["", "", ""])
                continue
            print(f"进入详情页：{book_url}")
            try:
                detail = parse_book_detail(page,book_url)
            except Exception as e:
                print(f"详情页异常，跳过：{e}")
                detail = None

            if detail:
                b.extend([detail["pages"],detail["isbn"],detail["intro"]])
                detail_done.add(book_url)

                # save_resume_point(keyword,page_num,detail_done)
            else:
                b.extend(["","",""])
            time.sleep(random.uniform(3,5))
        results.extend(books)


        #去脏
        # for b in books:
        #     # if b[0] not in seen:
        #         # seen.add(b[0])
        #         results.append(b)


        print(f" 本页 {len(books)} 条，累计 {len(results)} 条。")
        page_num += 1
        save_resume_point(keyword, page_num,detail_done)

        # # 安全兜底（防止被封死循环）
        # if page_num >= 50:
        #     print(" 已达到安全上限 50 页，强制停止")
        #     break
        time.sleep(random.uniform(2, 4))

    results.sort(key=lambda x: x[1], reverse=True)
    print(f"关键词 [{keyword}] 完成，共 {len(results)} 条")
    return results

def check_login(page):
    print("检查登录态")
    page.goto("https://book.douban.com/",wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    if "accounts.douban.com" in page.url or "login" in page.url.lower():
        print("未登录或登录失效，请先手动登录并保存状态")
        return False
    print("登录正常")
    return True

def main():
    wb = Workbook()
    wb.remove(wb.active)  # 删除默认 Sheet

    with sync_playwright() as p:
        #启动 Chromium 浏览器进程
        browser = p.chromium.launch(
            headless=False,  # 复用登录态，可无头
            args=["--disable-blink-features=AutomationControlled",
                  # "--disable-features=IsolateOrigins,site-per-process"

                  ] #禁用 blink 功能=自动化控制
        )
        #新建一个"浏览器上下文"（Context）
        context = browser.new_context(
            storage_state=STATE_FILE,  # 关键：复用登录态
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",

        )
        #在每个页面加载前，自动注入一段 JS 脚本。正常浏览器：navigator.webdriver === false 或 undefined
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )

        #在 Context 里开一个新标签页，拿到 page 对象。
        page = context.new_page()

        if not check_login(page):
            browser.close()
            raise SystemExit("请先运行一次login.py 生成有效的 douban_state.json")

        for kw in KEYWORDS:

            print(f"开始爬取关键词: {kw}")
            books = []
            try:
                books = scrape_keyword(page, kw)
            except Exception as e:
                print(f"关键词{kw}爬取失败：{e}")


            # 每个关键词一个 Sheet
            print(f" 正在为关键词 [{kw}] 创建 Sheet")
            sage_shhet_name = re.sub(r'[\\/*?:\[\]]','_',kw)[:31] # Sheet 名最长 31 字符
            ws = wb.create_sheet(title=sage_shhet_name)
            ws.append(["序号", "书名", "评分", "评价人数", "作者", "出版社","页数","ISBN","内容简介"])
            for idx, b in enumerate(books, 1):
                while len(b) < 9:
                    b.append("")
                ws.append([idx, b[0], b[1], b[2], b[3], b[4],b[6],b[7],b[8]])
            print(f" 关键词 [{kw}] 共 {len(books)} 条")

            sleep_time = random.uniform(5,8)
            print(f"休息{sleep_time}秒，再爬下一个关键词")
            time.sleep(sleep_time)

        browser.close()

    filename = "book-{}.xlsx".format(time.strftime("%Y%m%d_%H%M%S"))

    if wb.worksheets:
        wb.save(filename)
        print(f"\n 全部加载完成，已保存到 {filename}")
    else:
        print("\n本次没有爬取任何新关键词，未生成 Excel 文件")
if __name__ == "__main__":
    main()