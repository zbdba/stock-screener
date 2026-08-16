#!/usr/bin/env python3
"""拉取A股命中股 K线：腾讯 ifzq.gtimg.cn（日K70 + 周K60）+ 本地 MA10/20 趋势。
读取 /tmp/ascreener_hits.json。"""
import urllib.request, json, time
from concurrent.futures import ThreadPoolExecutor, as_completed

OUT = "/tmp"

def fetch(url, timeout=15, retry=3):
    last = None
    for i in range(retry):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com/"})
            return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")
        except Exception as e:
            last = e
            time.sleep(0.4 * (i + 1))
    return None

def kline(code, ktype, n):
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},{ktype},,,{n},qfq"
    txt = fetch(url, retry=3)
    if not txt:
        return []
    try:
        j = json.loads(txt)
        node = j["data"].get(code, {})
        arr = node.get("qfqday") or node.get("day") or node.get("qfqweek") or node.get("week") or []
    except Exception:
        return []
    rows = []
    for r in arr:
        try:
            rows.append((r[0], float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5])))
        except Exception:
            pass
    return rows

def ma_slope(vals, period):
    if len(vals) < period + 3:
        return None
    cur = sum(vals[-period:]) / period
    prev = sum(vals[-period - 3:-3]) / period
    return cur >= prev

with open(f"{OUT}/ascreener_hits.json") as f:
    a_codes = [h["code"] for h in json.load(f)["hits"]]
print(f"A股命中 {len(a_codes)} 只，开始拉取日K/周K（腾讯 ifzq）...")

day_rows = {}
week_rows = {}
ma_trend = {}

def work(code):
    d = kline(code, "day", 70)
    w = kline(code, "week", 60)
    return code, d, w

with ThreadPoolExecutor(max_workers=8) as ex:
    fut = {ex.submit(work, c): c for c in a_codes}
    done = 0
    for f in as_completed(fut):
        code = fut[f]
        done += 1
        _, d, w = f.result()
        if d:
            day_rows[code] = d
            closes = [r[2] for r in d]
            m10 = ma_slope(closes, 10)
            m20 = ma_slope(closes, 20)
            if m10 and m20:
                t = "both"
            elif m10:
                t = "ma10"
            elif m20:
                t = "ma20"
            else:
                t = None
            if t:
                ma_trend[code] = {"type": t}
        if w:
            week_rows[code] = w
        if done % 80 == 0:
            print(f"  进度 {done}/{len(a_codes)}")

with open(f"{OUT}/kl_day_new.txt", "w", encoding="utf-8") as f:
    f.write("| symbol | date | open | close | high | low | volume | amount | exchange |\n")
    for code in a_codes:
        for day, o, c, h, l, v in day_rows.get(code, []):
            f.write(f"| {code} | {day} | {o} | {c} | {h} | {l} | {int(v)} | | |\n")
with open(f"{OUT}/kl_week_new.txt", "w", encoding="utf-8") as f:
    f.write("| symbol | date | open | close | high | low | volume | amount | exchange |\n")
    for code in a_codes:
        for day, o, c, h, l, v in week_rows.get(code, []):
            f.write(f"| {code} | {day} | {o} | {c} | {h} | {l} | {int(v)} | | |\n")
with open(f"{OUT}/ma_trend.json", "w", encoding="utf-8") as f:
    json.dump(ma_trend, f, ensure_ascii=False, indent=2)
print(f"K线写入: 日K{sum(len(v) for v in day_rows.values())}条 周K{sum(len(v) for v in week_rows.values())}条; 均线趋势{len(ma_trend)}只 -> /tmp/kl_*_new.txt, /tmp/ma_trend.json")
