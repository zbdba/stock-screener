#!/usr/bin/env python3
"""抓取 49 只自选股行情(腾讯qt，按市场字段映射)。输出 /tmp/watchlist_data.json。"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qt_common as qc

# 与 gen_list.py / gen_watchlist_details.py 保持一致的自选股清单
WATCHLIST = [
    {"code": "sz002258", "name": "利尔化学", "mkt": "A"},
    {"code": "sh515880", "name": "通信ETF国泰", "mkt": "E"},
    {"code": "sz159915", "name": "创业板ETF易方达", "mkt": "E"},
    {"code": "sh515790", "name": "光伏ETF华泰柏瑞", "mkt": "E"},
    {"code": "sz159713", "name": "稀土ETF富国", "mkt": "E"},
    {"code": "sz159995", "name": "芯片ETF华夏", "mkt": "E"},
    {"code": "sh512710", "name": "军工龙头ETF富国", "mkt": "E"},
    {"code": "sh561380", "name": "电网设备ETF国泰", "mkt": "E"},
    {"code": "sz159326", "name": "电网设备ETF华夏", "mkt": "E"},
    {"code": "sh588170", "name": "科创半导体ETF华夏", "mkt": "E"},
    {"code": "sz159559", "name": "机器人ETF景顺", "mkt": "E"},
    {"code": "sh563230", "name": "卫星ETF富国", "mkt": "E"},
    {"code": "sh513120", "name": "港股创新药ETF广发", "mkt": "E"},
    {"code": "sh562500", "name": "机器人ETF华夏", "mkt": "E"},
    {"code": "sz399673", "name": "创业板50", "mkt": "I"},
    {"code": "usGOTU", "name": "高途", "mkt": "U"},
    {"code": "usSOXS", "name": "三倍做空半导体ETF", "mkt": "L"},
    {"code": "usMSTR", "name": "微策略", "mkt": "U"},
    {"code": "usSQQQ", "name": "三倍做空纳指ETF", "mkt": "L"},
    {"code": "usSG", "name": "Sweetgreen", "mkt": "U"},
    {"code": "usVCYT", "name": "Veracyte", "mkt": "U"},
    {"code": "usTSLA", "name": "特斯拉", "mkt": "U"},
    {"code": "usSEZL", "name": "Sezzle", "mkt": "U"},
    {"code": "usAUR", "name": "Aurora Innovation", "mkt": "U"},
    {"code": "usLULU", "name": "Lululemon", "mkt": "U"},
    {"code": "usTEM", "name": "Tempus AI", "mkt": "U"},
    {"code": "usSGML", "name": "Sigma Lithium", "mkt": "U"},
    {"code": "usNFLX", "name": "奈飞", "mkt": "U"},
    {"code": "usVIR", "name": "Vir Biotech", "mkt": "U"},
    {"code": "usLUNR", "name": "直觉机器", "mkt": "U"},
    {"code": "usRDW", "name": "Redwire", "mkt": "U"},
    {"code": "usSERV", "name": "Serve Robotics", "mkt": "U"},
]

a_codes, us_codes = [], []
for w in WATCHLIST:
    if w["code"].startswith("us"):
        us_codes.append(w["code"])
    else:
        a_codes.append(w["code"])  # sh/sz 含 ETF/指数，用A股88字段

print(f"查询 {len(a_codes)} A/ETF/指数 + {len(us_codes)} 美股...", flush=True)
a_data = qc.qt_batch_a(a_codes)
u_data = qc.qt_batch_us(us_codes)
merged = {}
merged.update(a_data)
merged.update(u_data)

out = []
for w in WATCHLIST:
    q = merged.get(w["code"], {})
    out.append({
        "code": w["code"], "name": w["name"], "mkt": w["mkt"],
        "price": q.get("price", 0), "pe": q.get("pe", 0), "mcap": q.get("mcap", 0),
        "chgpct": q.get("chgpct", 0), "chg5d": q.get("chg5d", 0),
        "chg10d": q.get("chg10d", 0), "chg20d": q.get("chg20d", 0), "chg60d": q.get("chg60d", 0),
    })

json.dump(out, open("/tmp/watchlist_data.json", "w"), ensure_ascii=False, indent=2)
print(f"DONE: {len(out)} 只自选股行情写入 /tmp/watchlist_data.json", flush=True)
for o in out:
    print(f"  {o['name']}({o['code']}) 现价={o['price']:.2f} 60d={o['chg60d']:+.1f}% 10d={o['chg10d']:+.1f}%", flush=True)
