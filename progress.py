#记住“下次从哪开始”

import json
import os
from config import PROGRESS_FILE

def load_progress():
    """读取断点文件，返回 {keyword: {"page": x, "detail_done": [...]}}"""
    if not os.path.exists(PROGRESS_FILE):
        return {}

    with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 兼容旧格式
    if isinstance(data, list):
        return {k: {"page": 0, "detail_done": []} for k in data}

    for k, v in data.items():
        if isinstance(v, int):
            data[k] = {"page": v, "detail_done": []}
        elif "detail_done" not in v:
            data[k]["detail_done"] = []

    return data


def save_progress(keyword, next_page, detail_done):
    """
    保存“下次从哪开始”
    next_page: 下一次要爬的页码（不是刚爬完的）
    """
    prog = load_progress()
    prog[keyword] = {
        "page": next_page,
        "detail_done": sorted(detail_done),
    }
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(prog, f, ensure_ascii=False, indent=2)