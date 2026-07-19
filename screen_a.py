#!/usr/bin/env python3
"""A股全量超跌反弹筛选（腾讯qt + 新浪代码）。输出 /tmp/ascreener_hits.json。"""
import os, sys, json
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qt_common as qc

print("STEP1: 拉取全A股代码(新浪 hs_a)...", flush=True)
codes = qc.get_sina_codes("hs_a")
print(f"  A股代码数: {len(codes)}", flush=True)


def screen_batch(batch):
    d = qc.qt_batch_a(batch)
    out = []
    for code, q in d.items():
        pe = q["pe"]; c60 = q["chg60d"]; c10 = q["chg10d"]
        if pe > 0 and pe <= 50 and c60 < -20 and c10 > 0:
            out.append({"code": code, "name": q["name"], "pe": pe, "chgpct": q["chgpct"],
                        "chg5d": q["chg5d"], "chg10d": c10, "chg20d": q["chg20d"],
                        "chg60d": c60, "price": q["price"], "mcap": q["mcap"], "strict": True})
    return out


batches = [codes[i:i + 50] for i in range(0, len(codes), 50)]
hits = []
seen = set()

with ThreadPoolExecutor(max_workers=6) as ex:
    futs = {ex.submit(screen_batch, b): b for b in batches}
    done = 0
    for f in as_completed(futs):
        done += 1
        for h in f.result():
            if h["code"] not in seen:
                seen.add(h["code"]); hits.append(h)
        if done % 40 == 0:
            print(f"  ...{done}/{len(batches)} batches, hits={len(hits)}", flush=True)

print(f"严格命中(60d<-20): {len(hits)}", flush=True)


def relax(threshold, key):
    if len(hits) >= 6:
        return
    print(f"  不足6只，放宽到 chg60d<-{threshold}...", flush=True)
    for batch in batches:
        d = qc.qt_batch_a(batch)
        for code, q in d.items():
            if code in seen:
                continue
            pe = q["pe"]; c60 = q["chg60d"]; c10 = q["chg10d"]
            if pe > 0 and pe <= 50 and c60 < -threshold and c10 > 0:
                seen.add(code)
                hits.append({"code": code, "name": q["name"], "pe": pe, "chgpct": q["chgpct"],
                            "chg5d": q["chg5d"], "chg10d": c10, "chg20d": q["chg20d"],
                            "chg60d": c60, "price": q["price"], "mcap": q["mcap"],
                            "strict": False, key: True})
    print(f"  放宽后 hits={len(hits)}", flush=True)


relax(15, "relaxed")
relax(10, "relaxed2")

hits.sort(key=lambda h: h["chg60d"])
json.dump({"hits": hits, "total_scanned": len(codes), "updated": qc.TODAY},
          open("/tmp/ascreener_hits.json", "w"), ensure_ascii=False, indent=2)
print(f"\nFINAL: A股命中 {len(hits)} / 扫描 {len(codes)}", flush=True)
for h in hits[:40]:
    tag = " [二级-10%]" if h.get("relaxed2") else (" [降级-15%]" if h.get("relaxed") else "")
    print(f"  {h['name']}({h['code']}) PE={h['pe']:.1f} 60d={h['chg60d']:.1f}% 10d={h['chg10d']:.1f}%{tag}", flush=True)
