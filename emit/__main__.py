#!/usr/bin/env python3
"""
emit 모듈 — 독립 실행 진입점.
GoldenBough Orchestrator가 subprocess로 호출할 때 사용.
"""
import sys
import os
import json
from pathlib import Path

# ROOT 경로 설정
ROOT = Path(os.environ.get("GOLDEN_BOUGH_ROOT", Path(__file__).parent.parent.resolve()))
sys.path.insert(0, str(ROOT))

# emit 모듈 로드
from emit.emit import run_once

if __name__ == "__main__":
    # 옵션 인자 파싱
    import argparse
    parser = argparse.ArgumentParser(description="Emit 모듈 — 데이터 방출")
    parser.add_argument("--channels", nargs="+", default=["html", "md", "json"], help="방출 채널")
    args = parser.parse_args()

    # 데이터 방출 실행
    result = run_once(channels=args.channels)

    # JSON 결과 출력
    output = {
        "stage": "emit",
        "n_cards": result.get("n_cards", 0),
        "emitted": result.get("emitted", {}),
        "status": "success"
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
