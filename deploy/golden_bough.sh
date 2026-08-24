#!/usr/bin/env bash
# ===================================================================
# 황금가지 무한동력 에이전트 - 배포/실행 스크립트
# ===================================================================
# 사용법:
#   bash deploy/golden_bough.sh once                    # 1회 풀사이클
#   bash deploy/golden_bough.sh once-llm                # LLM 활성화 1회
#   bash deploy/golden_bough.sh ingest                  # 흡입만
#   bash deploy/golden_bough.sh filter                  # 선별만
#   bash deploy/golden_bough.sh transform               # 변환만
#   bash deploy/golden_bough.sh emit                    # 방출만
#   bash deploy/golden_bough.sh feedback                # 재점화만
#   bash deploy/golden_bough.sh status                  # 상태
#   bash deploy/golden_bough.sh log                     # 최근 로그
#   bash deploy/golden_bough.sh install-cron            # 30분마다 자동실행
#   bash deploy/golden_bough.sh remove-cron             # 자동실행 제거
# ===================================================================

set -e

ROOT="${GOLDEN_BOUGH_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
LOGS="$ROOT/logs"
mkdir -p "$LOGS"

cmd="${1:-once}"

case "$cmd" in
  once)
    cd "$ROOT"
    python3 deploy/pipeline.py --simulate-feedback 2>&1 | tee -a "$LOGS/run.log"
    ;;
  once-llm)
    cd "$ROOT"
    python3 deploy/pipeline.py --simulate-feedback --llm 2>&1 | tee -a "$LOGS/run.log"
    ;;
  ingest)
    cd "$ROOT"
    python3 ingest/ingest.py 2>&1 | tee -a "$LOGS/ingest.log"
    ;;
  filter)
    cd "$ROOT"
    python3 filter/filter.py 2>&1 | tee -a "$LOGS/filter.log"
    ;;
  transform)
    cd "$ROOT"
    python3 transform/transform.py 2>&1 | tee -a "$LOGS/transform.log"
    ;;
  emit)
    cd "$ROOT"
    python3 emit/emit.py 2>&1 | tee -a "$LOGS/emit.log"
    ;;
  feedback)
    cd "$ROOT"
    python3 feedback/feedback.py 2>&1 | tee -a "$LOGS/feedback.log"
    ;;
  status)
    echo "=== 🏵️ GoldenBough Status ==="
    echo ""
    echo "📂 Raw data:"
    find "$ROOT/data/raw" -type f -name "*.jsonl" 2>/dev/null | wc -l
    echo "   Last: $(ls -t $ROOT/data/raw/*/*.jsonl 2>/dev/null | head -1)"
    echo ""
    echo "🔍 Curated:"
    find "$ROOT/data/curated" -type f -name "*.jsonl" 2>/dev/null | wc -l
    echo "   Last: $(ls -t $ROOT/data/curated/*/*.jsonl 2>/dev/null | head -1)"
    echo ""
    echo "🔄 Cards (knowledge):"
    find "$ROOT/data/knowledge" -type f -name "*.jsonl" 2>/dev/null | wc -l
    echo ""
    echo "📤 Outputs:"
    ls -lh "$ROOT/data/output/" 2>/dev/null
    echo ""
    echo "🔥 Feedback entries:"
    [ -f "$ROOT/data/feedback/feedback.jsonl" ] && wc -l "$ROOT/data/feedback/feedback.jsonl" || echo "0"
    echo ""
    echo "💾 Disk usage:"
    du -sh "$ROOT/data" 2>/dev/null
    echo ""
    echo "⏰ Cron:"
    crontab -l 2>/dev/null | grep -i golden || echo "  (no cron entry)"
    ;;
  log)
    tail -50 "$LOGS/run.log" 2>/dev/null || echo "no log yet"
    ;;
  install-cron)
    echo "📦 Cron 등록: 30분마다"
    CRON_LINE="*/30 * * * * cd $ROOT && /usr/bin/python3 deploy/pipeline.py --simulate-feedback >> $LOGS/cron.log 2>&1"
    (crontab -l 2>/dev/null | grep -v "golden_bough\|deploy/pipeline"; echo "$CRON_LINE") | crontab -
    echo "✅ Cron 등록 완료:"
    crontab -l | grep pipeline
    ;;
  remove-cron)
    echo "🗑️ Cron 제거"
    crontab -l 2>/dev/null | grep -v "deploy/pipeline" | crontab -
    echo "✅ Cron 제거 완료"
    ;;
  *)
    echo "Usage: bash deploy/golden_bough.sh {once|once-llm|ingest|filter|transform|emit|feedback|status|log|install-cron|remove-cron}"
    exit 1
    ;;
esac
