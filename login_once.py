# -*- coding: utf-8 -*-
"""第一步：手动登录豆瓣，保存登录态（只需运行一次）"""

import time
from playwright.sync_api import sync_playwright

STATE_FILE = "douban_state.json" #状态文件

with sync_playwright() as p:
    browser = p.chromium.launch(headless= False)  # 可见，方便手动登录
    context = browser.new_context()
    page = context.new_page()

    page.goto("https://book.douban.com/subject_search?search_text=时间管理")

    print("请在弹出的浏览器中完成登录")
    print("登录成功后，回到这里，等待30秒自动倒计时结束...")

    # 30 秒手动操作时间
    for i in range(30, 0, -1):
        print(f"  {i} 秒后自动保存douban_state.json", end="\r")
        time.sleep(1)

    context.storage_state(path=STATE_FILE)
    print(f"登录态已保存到 {STATE_FILE}，之后可 headless 自动运行")
    browser.close()