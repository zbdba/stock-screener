#!/usr/bin/env python3
"""A股96只宽基指数超跌反弹扫描（腾讯qt）。输出 /tmp/index_hits.json。"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qt_common as qc

CORE_WIDE = ["sh000001","sz399001","sz399006","sh000300","sh000905","sh000852","sh000016","sh000688","sz399005","sz399673","sh000903","sz399106","sh000009","sh000010"]
STYLE = ["sh000015","sh000821","sh000922","sh000058","sh000059","sh000028","sh000029","sz399370","sz399371","sz399372","sz399373","sz399375","sz399377","sz399645"]
CONSUME = ["sh000069","sh000074","sh000126","sh000932","sh000807","sz399617","sz399646","sz399987"]
PHARMA = ["sh000075","sh000121","sh000808","sh000814","sh000841","sh000913","sz399674","sz399989"]
FINANCE = ["sh000018","sh000076","sh000134","sz399619","sz399986","sz399975","sz399637","sh000006"]
TECH = ["sh000039","sh000915","sz399610","sz399363","sz399699","sz399811","sz399967","sz399973","sz399368","sz399959"]
ENERGY = ["sh000032","sh000066","sh000068","sh000033","sh000819","sh000823","sz399613","sz399614","sz399639","sh000820"]
INDUSTRY = ["sh000072","sh000034","sh000025","sh000910","sz399615","sz399803","sh000097","sz399636"]
OPTIONAL = ["sh000073","sh000035","sh000911","sz399616","sh000041","sz399638","sh000941","sz399808"]
TELECOM = ["sh000040","sh000916","sz399675","sz399677","sz399971","sz399805"]
AGRI = ["sh000122","sh000063"]
ALL = CORE_WIDE+STYLE+CONSUME+PHARMA+FINANCE+TECH+ENERGY+INDUSTRY+OPTIONAL+TELECOM+AGRI
CAT = {}
for c in CORE_WIDE: CAT[c]="核心宽基"
for c in STYLE: CAT[c]="风格策略"
for c in CONSUME: CAT[c]="消费"
for c in PHARMA: CAT[c]="医药"
for c in FINANCE: CAT[c]="金融地产"
for c in TECH: CAT[c]="科技军工"
for c in ENERGY: CAT[c]="能源资源"
for c in INDUSTRY: CAT[c]="工业制造"
for c in OPTIONAL: CAT[c]="可选公用"
for c in TELECOM: CAT[c]="通信传媒"
for c in AGRI: CAT[c]="农业周期"

print(f"扫描 {len(ALL)} 只指数...", flush=True)
all_data = []
batches = [ALL[i:i+40] for i in range(0, len(ALL), 40)]
for b in batches:
    d = qc.qt_batch_a(b)
    for code in b:
        q = d.get(code)
        if not q or not q.get("name"):
            continue
        c60 = q["chg60d"]; c5 = q["chg5d"]
        status = "hit" if (c60 < -10 and c5 > 0) else ("watch" if c60 < -10 else "normal")
        all_data.append({"code": code, "name": q["name"], "category": CAT.get(code, "其他"),
                        "price": q["price"], "chg_today": q["chgpct"], "chg_5d": c5,
                        "chg_10d": q["chg10d"], "chg_20d": q["chg20d"], "chg_60d": c60, "status": status})

json.dump({"total": len(all_data), "indices": all_data}, open("/tmp/index_all_96.json", "w"), ensure_ascii=False, indent=2)
hits = [h for h in all_data if h["status"] in ("hit", "watch")]
json.dump({"index_hits": hits}, open("/tmp/index_hits.json", "w"), ensure_ascii=False, indent=2)
hit_cnt = sum(1 for h in hits if h["status"] == "hit")
watch_cnt = sum(1 for h in hits if h["status"] == "watch")
print(f"超跌反弹(hit)={hit_cnt}  观察中(watch)={watch_cnt}", flush=True)
for h in hits:
    print(f"  {'✅' if h['status']=='hit' else '👁'} {h['name']}({h['code']}) [{h['category']}] 60d={h['chg_60d']:.2f}% 5d={h['chg_5d']:.2f}%", flush=True)
