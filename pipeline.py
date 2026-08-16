#!/usr/bin/env python3
"""统一流水线：补齐股票 skill 断裂的数据环节。
数据来源（按 SKILL.md 文档）：
 - A股代码池：新浪财经 API (hs_a + sz_a)
 - 行情/涨跌幅/PE/市值：腾讯 qt API（GBK 解码，按市场区分字段）
 - K线：新浪日K API（聚合周K），本地计算 MA10/MA20 趋势

产出：
 /tmp/watchlist_data.json   自选股行情（49 只，含 nodata 跳过）
 /tmp/ascreener_hits.json   A股超跌反弹命中（hits 列表）
 /tmp/index_hits.json       宽基指数命中
 /tmp/index_all_96.json     宽基指数全量
 /tmp/kl_day_new.txt        A股命中股日K
 /tmp/kl_week_new.txt       A股命中股周K（聚合）
 /tmp/ma_trend.json         MA10/20 均线趋势标签
"""
import urllib.request, json, time, sys, os, re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

TODAY = date.today().strftime("%Y-%m-%d")
OUT = "/tmp"

# ============================ 取数工具 ============================
def fetch(url, decode="utf-8", timeout=15, retry=3):
    last = None
    for i in range(retry):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            raw = urllib.request.urlopen(req, timeout=timeout).read()
            return raw.decode(decode, "replace")
        except Exception as e:
            last = e
            time.sleep(0.4 * (i + 1))
    print("WARN fetch fail:", url[:90], "->", last)
    return None

# ============================ 自选股行情 ============================
WATCHLIST = [
    ("sz002258","利尔化学"),("sh515880","通信ETF国泰"),("sz159915","创业板ETF易方达"),
    ("sh515790","光伏ETF华泰柏瑞"),("sz159713","稀土ETF富国"),("sz159995","芯片ETF华夏"),
    ("sh512710","军工龙头ETF富国"),("sh561380","电网设备ETF国泰"),("sz159326","电网设备ETF华夏"),
    ("sh588170","科创半导体ETF华夏"),("sz159559","机器人ETF景顺"),("sh563230","卫星ETF富国"),
    ("sh513120","港股创新药ETF广发"),("sh562500","机器人ETF华夏"),("sz399673","创业板50"),
    ("usGOTU","高途"),("usSOXS","三倍做空半导体ETF"),("usMSTR","微策略"),("usSQQQ","三倍做空纳指ETF"),
    ("usSG","Sweetgreen"),("usVCYT","Veracyte"),("usTSLA","特斯拉"),("usSEZL","Sezzle"),
    ("usAUR","Aurora Innovation"),("usLULU","Lululemon"),("usTEM","Tempus AI"),("usSGML","Sigma Lithium"),
    ("usNFLX","奈飞"),("usVIR","Vir Biotech"),("usLUNR","直觉机器"),("usRDW","Redwire"),("usSERV","Serve Robotics"),
]

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

def parse_by_market(code, p):
    try:
        if code.startswith("sh") or code.startswith("sz"):
            return dict(name=p[1], price=float(p[3]), chgpct=float(p[32]),
                        pe=float(p[39]) if p[39] else 0,
                        mcap=float(p[44]) if p[44] else 0,
                        chg5d=float(p[63]) if p[63] else 0,
                        chg10d=float(p[69]) if p[69] else 0,
                        chg20d=float(p[70]) if p[70] else 0,
                        chg60d=float(p[71]) if p[71] else 0)
        elif code.startswith("us"):
            return dict(name=p[1], price=float(p[3]), chgpct=float(p[32]),
                        pe=float(p[39]) if p[39] else 0,
                        mcap=float(p[44]) if p[44] else 0,
                        chg5d=float(p[55]) if p[55] else 0,
                        chg10d=float(p[59]) if p[59] else 0,
                        chg20d=float(p[60]) if p[60] else 0,
                        chg60d=float(p[61]) if p[61] else 0)
        elif code.startswith("hk"):
            return dict(name=p[1], price=float(p[3]), chgpct=float(p[32]),
                        pe=float(p[39]) if p[39] else 0,
                        mcap=float(p[44]) if p[44] else 0,
                        chg5d=float(p[62]) if p[62] else 0,
                        chg10d=float(p[66]) if p[66] else 0,
                        chg20d=float(p[67]) if p[67] else 0,
                        chg60d=float(p[68]) if p[68] else 0)
    except Exception:
        return None
    return None

print("== 自选股行情 ==")
wl_codes = [c for c, _ in WATCHLIST]
wl_map = {c: n for c, n in WATCHLIST}
wl_quotes = []
for i in range(0, len(wl_codes), 40):
    batch = wl_codes[i:i + 40]
    q = qt_batch(batch)
    for code in batch:
        p = q.get(code)
        if not p:
            continue
        d = parse_by_market(code, p)
        if not d:
            continue
        d["code"] = code
        wl_quotes.append(d)
        print(f"  {wl_map.get(code, code)}({code}) 价{d['price']} 60d{d['chg60d']:+.1f}% 10d{d['chg10d']:+.1f}%")
    time.sleep(0.15)
with open(f"{OUT}/watchlist_data.json", "w", encoding="utf-8") as f:
    json.dump(wl_quotes, f, ensure_ascii=False, indent=2)
print(f"自选股行情写入: {len(wl_quotes)} 条")

# ============================ A股代码池（新浪） ============================
print("\n== A股代码池（新浪 hs_a + sz_a）==")
all_codes = []
for node in ("hs_a", "sz_a"):
    pg = 1
    while True:
        txt = fetch(f"http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page={pg}&num=100&node={node}")
        if not txt:
            break
        try:
            arr = json.loads(txt)
        except Exception:
            break
        if not arr:
            break
        for it in arr:
            sym = it.get("symbol", "")
            if sym.startswith("sh") or sym.startswith("sz"):
                all_codes.append(sym)
        if len(arr) < 100:
            break
        pg += 1
        time.sleep(0.05)
print(f"A股代码池: {len(all_codes)} 只")

# ============================ A股行情 + 筛选（单遍扫描） ============================
print("\n== A股行情扫描 + 超跌反弹筛选 ==")
quotes = {}
for i in range(0, len(all_codes), 50):
    batch = all_codes[i:i + 50]
    q = qt_batch(batch)
    for code in batch:
        p = q.get(code)
        if not p:
            continue
        d = parse_by_market(code, p)
        if d:
            quotes[code] = d
    if (i // 50) % 20 == 0:
        print(f"  扫描进度 {i}/{len(all_codes)}")
    time.sleep(0.08)
print(f"有效A股行情: {len(quotes)} 只")

def screen(th60, strict_tag):
    hits = []
    for code, d in quotes.items():
        pe = d["pe"]
        if pe > 0 and pe <= 50 and d["chg60d"] < th60 and d["chg10d"] > 0:
            h = {"code": code, "name": d["name"], "pe": round(pe, 1),
                 "price": round(d["price"], 2), "chgpct": round(d["chgpct"], 2),
                 "chg5d": round(d["chg5d"], 2), "chg10d": round(d["chg10d"], 2),
                 "chg20d": round(d["chg20d"], 2), "chg60d": round(d["chg60d"], 2),
                 "mcap": round(d["mcap"], 1), "strict": strict_tag == "strict",
                 "relaxed": strict_tag != "strict", "relaxed2": strict_tag == "relaxed2"}
            hits.append(h)
    return hits

strict = screen(-20, "strict")
print(f"严格命中(chg60d<-20): {len(strict)}")
final = list(strict)
if len(final) < 6:
    r1 = [h for h in screen(-15, "relaxed") if h["code"] not in {x["code"] for x in final}]
    final += r1
    print(f"放宽-15% 追加: {len(r1)} (累计 {len(final)})")
if len(final) < 6:
    r2 = [h for h in screen(-10, "relaxed2") if h["code"] not in {x["code"] for x in final}]
    final += r2
    print(f"放宽-10% 追加: {len(r2)} (累计 {len(final)})")

with open(f"{OUT}/ascreener_hits.json", "w", encoding="utf-8") as f:
    json.dump({"hits": final, "total_scanned": len(quotes), "updated": TODAY}, f, ensure_ascii=False, indent=2)
print(f"A股命中写入: {len(final)} 只 -> /tmp/ascreener_hits.json")

# ============================ 宽基指数扫描 ============================
print("\n== 宽基指数扫描（96只）==")
CORE_WIDE=["sh000001","sz399001","sz399006","sh000300","sh000905","sh000852","sh000016","sh000688","sz399005","sz399673","sh000903","sz399106","sh000009","sh000010"]
STYLE=["sh000015","sh000821","sh000922","sh000058","sh000059","sh000028","sh000029","sz399370","sz399371","sz399372","sz399373","sz399375","sz399377","sz399645"]
CONSUME=["sh000069","sh000074","sh000126","sh000932","sh000807","sz399617","sz399646","sz399987"]
PHARMA=["sh000075","sh000121","sh000808","sh000814","sh000841","sh000913","sz399674","sz399989"]
FINANCE=["sh000018","sh000076","sh000134","sz399619","sz399986","sz399975","sz399637","sh000006"]
TECH=["sh000039","sh000915","sz399610","sz399363","sz399699","sz399811","sz399967","sz399973","sz399368","sz399959"]
ENERGY=["sh000032","sh000066","sh000068","sh000033","sh000819","sh000823","sz399613","sz399614","sz399639","sh000820"]
INDUSTRY=["sh000072","sh000034","sh000025","sh000910","sz399615","sz399803","sh000097","sz399636"]
OPTIONAL=["sh000073","sh000035","sh000911","sz399616","sh000041","sz399638","sh000941","sz399808"]
TELECOM=["sh000040","sh000916","sz399675","sz399677","sz399971","sz399805"]
AGRI=["sh000122","sh000063"]
ALL_IDX = CORE_WIDE+STYLE+CONSUME+PHARMA+FINANCE+TECH+ENERGY+INDUSTRY+OPTIONAL+TELECOM+AGRI
CAT={}
for c,grp in [(CORE_WIDE,"核心宽基"),(STYLE,"风格策略"),(CONSUME,"消费"),(PHARMA,"医药"),(FINANCE,"金融地产"),(TECH,"科技军工"),(ENERGY,"能源资源"),(INDUSTRY,"工业制造"),(OPTIONAL,"可选公用"),(TELECOM,"通信传媒"),(AGRI,"农业周期")]:
    for x in c: CAT[x]=grp

idx_all=[]
for i in range(0, len(ALL_IDX), 40):
    batch=ALL_IDX[i:i+40]
    q=qt_batch(batch)
    for code in batch:
        p=q.get(code)
        if not p: continue
        try:
            name=p[1]
            price=float(p[3]); chg_today=float(p[32])
            chg5d=float(p[63]) if p[63] else 0
            chg10d=float(p[69]) if p[69] else 0
            chg20d=float(p[70]) if p[70] else 0
            chg60d=float(p[71]) if p[71] else 0
        except Exception:
            continue
        if not name: continue
        cat=CAT.get(code,"其他")
        if chg60d < -10 and chg5d > 0: status="hit"
        elif chg60d < -10: status="watch"
        else: status="normal"
        idx_all.append({"code":code,"name":name,"category":cat,"price":round(price,2),
                        "chg_today":round(chg_today,2),"chg_5d":round(chg5d,2),"chg_10d":round(chg10d,2),
                        "chg_20d":round(chg20d,2),"chg_60d":round(chg60d,2),"status":status})
    time.sleep(0.1)
idx_hits=[h for h in idx_all if h["status"] in ("hit","watch")]
with open(f"{OUT}/index_all_96.json","w",encoding="utf-8") as f:
    json.dump({"total":len(idx_all),"indices":idx_all},f,ensure_ascii=False,indent=2)
with open(f"{OUT}/index_hits.json","w",encoding="utf-8") as f:
    json.dump({"index_hits":idx_hits},f,ensure_ascii=False,indent=2)
hit_cnt=sum(1 for h in idx_hits if h["status"]=="hit")
print(f"指数扫描 {len(idx_all)} 只; 命中(hit){hit_cnt} 观察(watch){len(idx_hits)-hit_cnt} -> /tmp/index_hits.json")

# ============================ K线 + 均线趋势 ============================
print("\n== 拉取A股命中股 K线（新浪日K）==")
a_codes=[h["code"] for h in final]

def kline_daily(code, n=70):
    url=f"https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={code}&scale=240&ma=5&datalen={n}"
    txt=fetch(url, timeout=15, retry=3)
    if not txt: return []
    try:
        arr=json.loads(txt)
    except Exception:
        return []
    rows=[]
    for k in arr:
        try:
            rows.append((k["day"], float(k["open"]), float(k["close"]), float(k["high"]), float(k["low"]), float(k["volume"])))
        except Exception:
            pass
    return rows

day_rows={}
week_rows={}
ma_trend={}
def ma_slope(vals, period):
    if len(vals) < period + 3:
        return None
    cur = sum(vals[-period:]) / period
    prev = sum(vals[-period-3:-3]) / period
    return cur >= prev

with ThreadPoolExecutor(max_workers=8) as ex:
    fut={ex.submit(kline_daily, c): c for c in a_codes}
    done=0
    for f in as_completed(fut):
        code=fut[f]; done+=1
        rows=f.result()
        if not rows:
            if done % 40 == 0: print(f"  K线进度 {done}/{len(a_codes)}")
            continue
        day_rows[code]=rows
        # 周K聚合
        wk={}
        for day,o,c,h,l,v in rows:
            yw=date.fromisoformat(day).isocalendar()[:2]
            if yw not in wk: wk[yw]=[day,o,c,h,l,v]
            else:
                e=wk[yw]; e[1]=e[1]; e[2]=c; e[3]=max(e[3],h); e[4]=min(e[4],l); e[5]+=v
        wk_rows[code]=[wk[k] for k in sorted(wk.keys())]
        # 均线趋势
        closes=[r[2] for r in rows]
        m10=ma_slope(closes,10); m20=ma_slope(closes,20)
        if m10 and m20: t="both"
        elif m10: t="ma10"
        elif m20: t="ma20"
        else: t=None
        if t: ma_trend[code]={"type":t}
        if done % 40 == 0:
            print(f"  K线进度 {done}/{len(a_codes)}")

# 写日K文件
with open(f"{OUT}/kl_day_new.txt","w",encoding="utf-8") as f:
    f.write("| symbol | date | open | close | high | low | volume | amount | exchange |\n")
    for code in a_codes:
        for day,o,c,h,l,v in day_rows.get(code, []):
            f.write(f"| {code} | {day} | {o} | {c} | {h} | {l} | {int(v)} | | |\n")
# 写周K文件
with open(f"{OUT}/kl_week_new.txt","w",encoding="utf-8") as f:
    f.write("| symbol | date | open | close | high | low | volume | amount | exchange |\n")
    for code in a_codes:
        for day,o,c,h,l,v in week_rows.get(code, []):
            f.write(f"| {code} | {day} | {o} | {c} | {h} | {l} | {int(v)} | | |\n")
with open(f"{OUT}/ma_trend.json","w",encoding="utf-8") as f:
    json.dump(ma_trend, f, ensure_ascii=False, indent=2)
print(f"K线写入: 日K{sum(len(v) for v in day_rows.values())}条 周K{sum(len(v) for v in week_rows.values())}条; 均线趋势{len(ma_trend)}只")

print("\n=== 流水线数据阶段完成 ===")
