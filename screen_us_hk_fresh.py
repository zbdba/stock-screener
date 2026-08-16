#!/usr/bin/env python3
"""美/港股超跌反弹筛选（腾讯qt，替代失效的 westock 脚本）。输出 data/screened_us_hk.json。"""
import urllib.request, json, time, os, sys
from datetime import date

TODAY = date.today().strftime("%Y-%m-%d")
SKILL_DATA = "/Users/bytedance/.workbuddy/skills/a-stock-screener/scripts/data"
OUT = os.path.join(SKILL_DATA, "screened_us_hk.json")

def fetch(url, decode="utf-8", timeout=15, retry=3):
    last = None
    for i in range(retry):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            return urllib.request.urlopen(req, timeout=timeout).read().decode(decode, "replace")
        except Exception as e:
            last = e
            time.sleep(0.4 * (i + 1))
    return None

def qt_batch(codes):
    url = "http://qt.gtimg.cn/q=" + ",".join(codes)
    txt = fetch(url, decode="gbk")
    out = {}
    if not txt:
        return out
    for line in txt.strip().split("\n"):
        if not line.startswith("v_"):
            continue
        code = line[2:line.index("=")]
        p = line[line.index('"') + 1:line.rindex('"')].split("~")
        out[code] = p
    return out

def parse_us(p):
    try:
        return dict(name=p[1], price=float(p[3]), chgpct=float(p[32]),
                    pe=float(p[39]) if p[39] else 0, mcap=float(p[44]) if p[44] else 0,
                    chg5d=float(p[55]) if p[55] else 0, chg10d=float(p[59]) if p[59] else 0,
                    chg20d=float(p[60]) if p[60] else 0, chg60d=float(p[61]) if p[61] else 0)
    except Exception:
        return None

def parse_hk(p):
    try:
        return dict(name=p[1], price=float(p[3]), chgpct=float(p[32]),
                    pe=float(p[39]) if p[39] else 0, mcap=float(p[44]) if p[44] else 0,
                    chg5d=float(p[62]) if p[62] else 0, chg10d=float(p[66]) if p[66] else 0,
                    chg20d=float(p[67]) if p[67] else 0, chg60d=float(p[68]) if p[68] else 0)
    except Exception:
        return None

with open(os.path.join(SKILL_DATA, "us_hk_list.json")) as f:
    pools = json.load(f)

def screen_market(symbols, prefix, parser, label):
    print(f"== {label} 筛选 ({len(symbols)} 只) ==")
    quotes = {}
    for i in range(0, len(symbols), 50):
        batch = symbols[i:i + 50]
        codes = [(prefix + s) for s in batch]
        q = qt_batch(codes)
        for s, code in zip(batch, codes):
            p = q.get(code)
            if not p:
                continue
            d = parser(p)
            if d:
                quotes[code] = d
        if (i // 50) % 10 == 0:
            print(f"  扫描 {i}/{len(symbols)}")
        time.sleep(0.08)
    print(f"  有效行情 {len(quotes)} 只")

    def filt(th60, tag):
        hits = []
        for code, d in quotes.items():
            if d["pe"] > 0 and d["chg60d"] < th60 and d["chg10d"] > 0:
                hits.append({"code": code, "name": d["name"], "market": prefix.lower(),
                             "price": round(d["price"], 2), "chgpct": round(d["chgpct"], 2),
                             "pe": round(d["pe"], 1), "mcap": round(d["mcap"], 1),
                             "chg5d": round(d["chg5d"], 2), "chg10d": round(d["chg10d"], 2),
                             "chg20d": round(d["chg20d"], 2), "chg60d": round(d["chg60d"], 2),
                             "strict": tag == "strict", "relaxed": tag != "strict",
                             "relaxed2": tag == "relaxed2"})
        return hits

    hits = filt(-20, "strict")
    extra = [h for h in filt(-15, "relaxed") if h["code"] not in {x["code"] for x in hits}]
    hits += extra
    if len(hits) < 6:
        extra2 = [h for h in filt(-10, "relaxed2") if h["code"] not in {x["code"] for x in hits}]
        hits += extra2
    print(f"  {label} 命中 {len(hits)} 只")
    return hits

us_syms = pools["us"]
hk_syms = [s.zfill(5) if len(s) < 5 else s for s in pools["hk"]]
us_hits = screen_market(us_syms, "us", parse_us, "美股")
hk_hits = screen_market(hk_syms, "hk", parse_hk, "港股")

with open(OUT, "w", encoding="utf-8") as f:
    json.dump({"us": us_hits, "hk": hk_hits, "updated": TODAY}, f, ensure_ascii=False, indent=2)
print(f"已写入 {OUT}: 美股{len(us_hits)} 港股{len(hk_hits)}")
