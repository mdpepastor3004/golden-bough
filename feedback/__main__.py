#!/usr/bin/env python3
"""
feedback 모듈 — 독립 실행 진입점.
GoldenBough Orchestrator가 subprocess로 호출할 때 사용.
"""
import sys
import os
import json
from pathlib import Path

# ROOT 경로 설정
ROOT = Path(os.environ.get("GOLDEN_BOUGH_ROOT", Path(__file__).parent.parent.resolve()))
sys.path.insert(0, str(ROOT))

# feedback 모듈 로드
from feedback.feedback import run_once

if __name__ == "__main__":
    # 옵션 인자 파싱
    import argparse
    parser = argparse.ArgumentParser(description="Feedback 모듈 — 가중치 재계산")
    parser.add_argument("--simulate-reactions", action="store_true", help="시뮬레이션 반응 주입")
    args = parser.parse_args()

    # 피드백 실행
    result = run_once(simulate_reactions=args.simulate_reactions)

    # JSON 결과 출력
    output = {
        "stage": "feedback",
        "weights_updated": bool(result.get("weights")),
        "weights": result.get("weights", {}),
        "status": "success"
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
