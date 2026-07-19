#!/bin/zsh
# 全市场超跌反弹 + 大盘趋势 + 宽基指数 → 列表页/详情页 → GitHub Pages 部署
# 一键重跑（顺序严格：gen_details 必须在 gen_list 之前，否则详情页链接缺失）
set -e
PY=/Users/bytedance/.workbuddy/binaries/python/versions/3.13.12/bin/python3
WS=/Users/bytedance/WorkBuddy/2026-07-19-23-33-08
SK=/Users/bytedance/.workbuddy/skills/a-stock-screener/scripts
LOG=/tmp/stock_run_all.log
cd "$WS"
echo "===== START $(date '+%F %T') =====" > "$LOG"
step() { echo "\n##### $1 #####" | tee -a "$LOG"; }

step "1. A股全量超跌筛选(腾讯qt+新浪)"; "$PY" screen_a.py >> "$LOG" 2>&1
step "2. 宽基指数96只扫描";               "$PY" screen_indices.py >> "$LOG" 2>&1
step "3. 自选股32只行情";                 "$PY" fetch_watchlist.py >> "$LOG" 2>&1
step "4. A股命中股日K/周K(新浪)";         "$PY" fetch_klines.py >> "$LOG" 2>&1
step "5. MA10/MA20均线趋势";              "$PY" calc_ma_trend.py >> "$LOG" 2>&1
step "6. 三市场大盘趋势资金流";           "$PY" "$SK/fetch_market_flow.py" >> "$LOG" 2>&1
step "7. 板块资金流数据";                 "$PY" "$SK/gen_sector_flow_data.py" >> "$LOG" 2>&1
step "8. 生成A股超跌详情页";              "$PY" "$SK/gen_details.py" >> "$LOG" 2>&1
step "9. 生成四Tab列表页(此时详情页已存在→链接注入)"; "$PY" "$SK/gen_list.py" >> "$LOG" 2>&1
step "10. 注入大盘趋势+内联echarts";      "$PY" "$SK/gen_market_trend.py" >> "$LOG" 2>&1

LINKS=$(grep -o 'stock_[a-z0-9]*\.html' index.html | sort -u | wc -l | tr -d ' ')
DET=$(ls stock_*.html 2>/dev/null | wc -l | tr -d ' ')
echo ">>> 详情页链接: $LINKS  /  详情页文件: $DET" | tee -a "$LOG"

step "11. 部署 GitHub Pages"
echo "" > .nojekyll
git add -A
git commit --allow-empty -q -m "deploy: 全市场超跌反弹+大盘趋势+宽基指数 ($(date '+%F %T') 重跑)" >> "$LOG" 2>&1
TOKEN=$(printf "protocol=https\nhost=github.com\n" | git credential fill 2>/dev/null | awk -F= '/^password/{print $2}')
git -c http.proxy= -c https.proxy= push --force -u "https://zbdba:${TOKEN}@github.com/zbdba/stock-screener.git" main >> "$LOG" 2>&1
echo "===== DONE $(date '+%F %T') =====" | tee -a "$LOG"
