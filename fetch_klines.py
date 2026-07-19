#!/usr/bin/env python3
"""抓取A股命中股的日K/周K(新浪fqkline)，写入 /tmp/kl_day_new.txt 与 /tmp/kl_week_new.txt。
格式(每行)：| code | date | open | close | high | low | volume | 0 | qfq |  —— 供 gen_details.py 解析。"""
import os, sys, json
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qt_common as qc

with open("/tmp/ascreener_hits.json") as f:
    codes = [h["code"] for h in json.load(f)["hits"]]
print(f"抓取 {len(codes)} 只A股命中股的K线...", flush=True)

day_rows = []
week_rows = []


def fetch_one(code):
    d = qc.get_kline(code, "day", 65)
    w = qc.get_kline(code, "week", 60)
    dl, wl = [], []
    for r in d:
        dl.append(f"| {code} | {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {int(r[5])} | 0 | qfq |")
    for r in w:
        wl.append(f"| {code} | {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {int(r[5])} | 0 | qfq |")
    return dl, wl


with ThreadPoolExecutor(max_workers=10) as ex:
    futs = {ex.submit(fetch_one, c): c for c in codes}
    done = 0
    for f in as_completed(futs):
        dl, wl = f.result()
        day_rows.extend(dl); week_rows.extend(wl)
        done += 1
        if done % 50 == 0:
            print(f"  ...{done}/{len(codes)}", flush=True)

with open("/tmp/kl_day_new.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(day_rows) + "\n")
with open("/tmp/kl_week_new.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(week_rows) + "\n")
print(f"DONE: 日K {len(day_rows)} 行, 周K {len(week_rows)} 行", flush=True)
