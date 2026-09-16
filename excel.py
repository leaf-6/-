#数据 → Excel

from openpyxl import Workbook
import re
import time

def save_excel(all_books: dict):
    wb = Workbook()
    wb.remove(wb.active)

    for kw, books in all_books.items():
        safe_name = re.sub(r'[\\/*?:\[\]]', '_', kw)[:31]
        ws = wb.create_sheet(title=safe_name)
        ws.append(["序号", "书名", "评分", "评价人数", "作者", "出版社", "页数", "ISBN", "内容简介"])

        for idx, b in enumerate(books, 1):
            while len(b) < 9:
                b.append("")
            ws.append([idx, b[0], b[1], b[2], b[3], b[4], b[6], b[7], b[8]])

    filename = f"book-{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
    wb.save(filename)
    print(f"\n已保存到 {filename}")