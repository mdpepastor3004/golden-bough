#!/usr/bin/env python3
"""
filter 모듈 — 독립 실행 진입점.
GoldenBough Orchestrator가 subprocess로 호출할 때 사용.
"""
import sys
import os
import json
from pathlib import Path

# ROOT 경로 설정
ROOT = Path(os.environ.get("GOLDEN_BOUGH_ROOT", Path(__file__).parent.parent.resolve()))
sys.path.insert(0, str(ROOT))

# filter 모듈 로드
from filter.filter import run_once

if __name__ == "__main__":
    # 데이터 선별 실행
    items = run_once()

    # JSON 결과 출력
    output = {
        "stage": "filter",
        "count": len(items),
        "items": items,
        "status": "success"
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
