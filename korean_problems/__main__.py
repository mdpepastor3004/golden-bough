#!/usr/bin/env python3
"""korean_problems 모듈 진입점"""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT))
from korean_problems.registry import run_proposal_loop
import json

if __name__ == "__main__":
    result = run_proposal_loop()
    print(json.dumps(result, ensure_ascii=False, indent=2))
