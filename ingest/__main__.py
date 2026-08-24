#!/usr/bin/env python3
"""
ingest 모듈 — 독립 실행 진입점.
GoldenBough Orchestrator가 subprocess로 호출할 때 사용.
한국 도메인 소스(korean_problems/sources.py)를 자동 머지하여 흡입.
"""
import sys
import os
import json
from pathlib import Path

ROOT = Path(os.environ.get("GOLDEN_BOUGH_ROOT", Path(__file__).parent.parent.resolve()))
sys.path.insert(0, str(ROOT))

from ingest.ingest import run_once, DEFAULT_RSS, DEFAULT_APIS, DEFAULT_STATIC

# 한국 도메인 소스 자동 머지
try:
    from korean_problems.sources import KOREAN_SOURCES
    # 한국 소스는 RSS 형태로 흡입되도록 변환
    korean_rss = []
    for ks in KOREAN_SOURCES:
        korean_rss.append({
            "name": ks["name"],
            "url": ks["url"],
            "category": ks.get("category", "general"),
            "weight": float(ks.get("weight", 1.0)),
        })
    # DEFAULT_RSS + 한국 RSS 머지 (중복 제거)
    rss_combined = list(DEFAULT_RSS)
    for ks in korean_rss:
        if not any(s.get("url") == ks["url"] for s in rss_combined):
            rss_combined.append(ks)
except Exception as e:
    rss_combined = DEFAULT_RSS
    print(f"⚠️  한국 소스 머지 실패: {e}", file=sys.stderr)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest 모듈 — 데이터 흡입")
    parser.add_argument("--parallel", action="store_true", help="병렬 수집 활성화")
    args = parser.parse_args()

    # 한국 소스 포함 흡입
    items = run_once(
        config={"rss": rss_combined, "apis": DEFAULT_APIS, "static": DEFAULT_STATIC},
        parallel=args.parallel,
    )

    output = {
        "stage": "ingest",
        "count": len(items),
        "items": items,
        "status": "success",
        "korean_sources_count": len(rss_combined) - len(DEFAULT_RSS),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
