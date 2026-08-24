#!/usr/bin/env python3
"""
transform 모듈 — 독립 실행 진입점.
GoldenBough Orchestrator가 subprocess로 호출할 때 사용.
"""
import sys
import os
import json
from pathlib import Path

# ROOT 경로 설정
ROOT = Path(os.environ.get("GOLDEN_BOUGH_ROOT", Path(__file__).parent.parent.resolve()))
sys.path.insert(0, str(ROOT))

# transform 모듈 로드
from transform.transform import run_once

if __name__ == "__main__":
    # 옵션 인자 파싱
    import argparse
    parser = argparse.ArgumentParser(description="Transform 모듈 — 데이터 변환")
    parser.add_argument("--use-llm", action="store_true", help="외부 LLM 사용")
    parser.add_argument("--llm-provider", default=None, help="LLM 프로바이더 (openai)")
    parser.add_argument("--max-items", type=int, default=50, help="최대 처리 개수")
    args = parser.parse_args()

    # 데이터 변환 실행
    cards = run_once(
        use_llm=args.use_llm,
        llm_provider=args.llm_provider,
        max_items=args.max_items
    )

    # JSON 결과 출력
    output = {
        "stage": "transform",
        "count": len(cards),
        "cards": cards,
        "status": "success"
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
