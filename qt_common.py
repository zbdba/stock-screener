#!/usr/bin/env python3
"""共享行情工具：腾讯qt(GBK) + 新浪代码 + 新浪K线。替代已失效的 westock quote/kline。"""
import urllib.request, json, time
from datetime import date

TODAY = date.today().strftime("%Y-%m-%d")
QT = "http://qt.gtimg.cn/q="
SINA = "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData"
KL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},{period},,,{n},qfq"

UA = {"User-Agent": "Mozilla/5.0"}


def http_get(url, timeout=15, decode="utf-8", retry=3):
    last = None
    for i in range(retry):
        try:
            req = urllib.request.Request(url, headers=UA)
            raw = urllib.request.urlopen(req, timeout=timeout).read()
            return raw.decode(decode, errors="replace")
        except Exception as e:
            last = e
            time.sleep(0.4 * (i + 1))
    return None


def get_sina_codes(node="hs_a", max_pages=80):
    codes = []
    for pg in range(1, max_pages + 1):
        url = f"{SINA}?page={pg}&num=100&node={node}&_s_r_a=auto"
        txt = http_get(url)
        if not txt:
            break
        try:
            data = json.loads(txt)
        except Exception:
            break
        if not data:
            break
        for s in data:
            codes.append(s["symbol"])
        if len(data) < 100:
            break
        time.sleep(0.12)
    return codes


def _parse_qt(line):
    if not line.startswith("v_"):
        return None
    code = line[2:line.index("=")]
    body = line[line.index('"') + 1:line.rindex('"')]
    return code, body.split("~")


def _flt(v):
    try:
        return float(v)
    except Exception:
        return 0.0


# A股 88字段: [3]现 [32]今% [39]PE [44]市值亿 [63]5d [69]10d [70]20d [71]60d
def qt_batch_a(codes):
    if not codes:
        return {}
    txt = http_get(QT + ",".join(codes), decode="gbk", timeout=20)
    if not txt:
        return {}
    out = {}
    for line in txt.strip().split("\n"):
        r = _parse_qt(line)
        if not r:
            continue
        code, p = r
        if len(p) < 72:
            continue
        out[code] = {
            "name": p[1], "price": _flt(p[3]), "chgpct": _flt(p[32]),
            "pe": (_flt(p[39]) if p[39] and p[39] != "0" else 0),
            "mcap": _flt(p[44]), "chg5d": _flt(p[63]),
            "chg10d": _flt(p[69]), "chg20d": _flt(p[70]), "chg60d": _flt(p[71]),
        }
    return out


# 美股 71字段: [3]现 [32]今% [39]PE [44]市值亿 [55]5d [59]10d [60]20d [61]60d
def qt_batch_us(codes):
    if not codes:
        return {}
    txt = http_get(QT + ",".join(codes), decode="gbk", timeout=20)
    if not txt:
        return {}
    out = {}
    for line in txt.strip().split("\n"):
        r = _parse_qt(line)
        if not r:
            continue
        code, p = r
        if len(p) < 62:
            continue
        out[code] = {
            "name": p[1], "price": _flt(p[3]), "chgpct": _flt(p[32]),
            "pe": (_flt(p[39]) if p[39] and p[39] != "0" else 0),
            "mcap": _flt(p[44]), "chg5d": _flt(p[55]),
            "chg10d": _flt(p[59]), "chg20d": _flt(p[60]), "chg60d": _flt(p[61]),
        }
    return out


# 港股 78字段: [3]现 [32]今% [39]PE [44]市值亿 [62]5d [66]10d [67]20d [68]60d
def qt_batch_hk(codes):
    if not codes:
        return {}
    txt = http_get(QT + ",".join(codes), decode="gbk", timeout=20)
    if not txt:
        return {}
    out = {}
    for line in txt.strip().split("\n"):
        r = _parse_qt(line)
        if not r:
            continue
        code, p = r
        if len(p) < 69:
            continue
        out[code] = {
            "name": p[1], "price": _flt(p[3]), "chgpct": _flt(p[32]),
            "pe": (_flt(p[39]) if p[39] and p[39] != "0" else 0),
            "mcap": _flt(p[44]), "chg5d": _flt(p[62]),
            "chg10d": _flt(p[66]), "chg20d": _flt(p[67]), "chg60d": _flt(p[68]),
        }
    return out


def get_kline(code, period, n=65):
    """新浪 fqkline。返回 [[date,open,close,high,low,vol],...] 升序。"""
    txt = http_get(KL.format(code=code, period=period, n=n), decode="utf-8", timeout=20)
    if not txt:
        return []
    try:
        j = json.loads(txt)
        node = j.get("data", {}).get(code, {})
        arr = node.get("qfqday") if period == "day" else node.get("qfqweek")
        if not arr:
            return []
        out = []
        for row in arr:
            if not row or len(row) < 5:
                continue
            out.append([row[0], _flt(row[1]), _flt(row[2]), _flt(row[3]), _flt(row[4]), _flt(row[5])])
        return out
    except Exception:
        return []
