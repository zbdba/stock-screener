#!/usr/bin/env python3
"""从 /tmp/kl_day_new.txt 计算各A股命中股的 MA10/MA20 均线趋势。
输出 /tmp/ma_trend.json：{code: {"type":"both"|"ma10"|"ma20"|None}}。"""
import json


def parse_table(path):
    rows = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line.startswith("|"):
                continue
            parts = [p.strip() for p in line.split("|")]
            parts = [p for p in parts if p]
            if len(parts) < 7 or parts[0] in ("symbol", "code", "---", ""):
                continue
            sym = parts[0]
            try:
                close = float(parts[3])  # [3]=close
            except Exception:
                continue
            rows.setdefault(sym, []).append(close)
    return rows


def ma_stop_down(closes, period):
    """最近3天 MA(period) 斜率 >= 0 视为停止向下。"""
    if len(closes) < period + 3:
        return False
    ma = []
    for i in range(len(closes)):
        if i < period - 1:
            ma.append(None)
        else:
            ma.append(sum(closes[i - period + 1:i + 1]) / period)
    try:
        return ma[-1] >= ma[-4]  # 今天 vs 3天前
    except Exception:
        return False


rows = parse_table("/tmp/kl_day_new.txt")
result = {}
for sym, closes in rows.items():
    if len(closes) < 25:
        continue
    ma10 = ma_stop_down(closes, 10)
    ma20 = ma_stop_down(closes, 20)
    if ma10 and ma20:
        t = "both"
    elif ma10:
        t = "ma10"
    elif ma20:
        t = "ma20"
    else:
        t = None
    if t:
        result[sym] = {"type": t}

json.dump(result, open("/tmp/ma_trend.json", "w"), ensure_ascii=False, indent=2)
print(f"MA趋势标记: {len(result)} 只 (双稳={sum(1 for v in result.values() if v['type']=='both')}, "
      f"MA10={sum(1 for v in result.values() if v['type']=='ma10')}, "
      f"MA20={sum(1 for v in result.values() if v['type']=='ma20')})", flush=True)
