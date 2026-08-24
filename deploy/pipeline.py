#!/usr/bin/env python3
"""
황금가지 무한동력 에이전트 - 통합 파이프라인 (Pipeline Orchestrator)
========================================================
흡입 → 선별 → 변환 → 방출 → 재점화 전체 사이클 실행
각 모듈을 순차/병렬로 호출하고 결과를 JSON으로 리포트.
"""
import json
import os
import time
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("GOLDEN_BOUGH_ROOT", Path(__file__).parent.parent.resolve()))
sys.path.insert(0, str(ROOT))

# 모듈 import
from ingest import ingest as ingest_mod
from filter import filter as filter_mod
from transform import transform as transform_mod
from emit import emit as emit_mod
from feedback import feedback as feedback_mod


def run_pipeline(use_llm=False, llm_provider=None, channels=None, dynamic_urls=None, simulate_feedback=False, verbose=True):
    """1회 전체 사이클."""
    channels = channels or ["html", "md", "json"]
    t0 = time.time()
    log = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "stages": {},
    }

    # ============================================================
    # Stage 1: 흡입
    # ============================================================
    if verbose:
        print("=" * 60)
        print("🏵️ Stage 1: 흡입 (Ingest)")
        print("=" * 60)
    t1 = time.time()
    dynamic = []
    if dynamic_urls:
        dynamic = [{"name": u.get("name", urlparse(u['url']).netloc), "url": u["url"], "category": u.get("category", "web"), "weight": u.get("weight", 1.0)} for u in dynamic_urls]
    raw_items = ingest_mod.run_once(parallel=True)
    log["stages"]["ingest"] = {"count": len(raw_items), "duration_sec": round(time.time() - t1, 2)}

    # ============================================================
    # Stage 2: 선별
    # ============================================================
    if verbose:
        print("\n" + "=" * 60)
        print("🔍 Stage 2: 선별 (Filter)")
        print("=" * 60)
    t2 = time.time()
    curated = filter_mod.run_once()
    log["stages"]["filter"] = {"count": len(curated), "duration_sec": round(time.time() - t2, 2)}

    # ============================================================
    # Stage 3: 변환
    # ============================================================
    if verbose:
        print("\n" + "=" * 60)
        print("🔄 Stage 3: 변환 (Transform)")
        print("=" * 60)
    t3 = time.time()
    cards = transform_mod.run_once(use_llm=use_llm, llm_provider=llm_provider, max_items=50)
    log["stages"]["transform"] = {"count": len(cards), "duration_sec": round(time.time() - t3, 2)}

    # ============================================================
    # Stage 4: 방출
    # ============================================================
    if verbose:
        print("\n" + "=" * 60)
        print("📤 Stage 4: 방출 (Emit)")
        print("=" * 60)
    t4 = time.time()
    emitted = emit_mod.run_once(channels=channels)
    log["stages"]["emit"] = {"n_cards": emitted.get("n_cards", 0), "channels": list(emitted.get("emitted", {}).keys()), "duration_sec": round(time.time() - t4, 2)}

    # ============================================================
    # Stage 5: 재점화
    # ============================================================
    if verbose:
        print("\n" + "=" * 60)
        print("🔥 Stage 5: 재점화 (Feedback)")
        print("=" * 60)
    t5 = time.time()
    feedback = feedback_mod.run_once(simulate_reactions=simulate_feedback)
    log["stages"]["feedback"] = {"weights_updated": bool(feedback.get("weights")), "duration_sec": round(time.time() - t5, 2)}

    # ============================================================
    # 총평
    # ============================================================
    log["finished_at"] = datetime.now(timezone.utc).isoformat()
    log["total_duration_sec"] = round(time.time() - t0, 2)

    if verbose:
        print("\n" + "=" * 60)
        print("✅ 파이프라인 완료")
        print("=" * 60)
        print(json.dumps(log, ensure_ascii=False, indent=2))

    # 파이프라인 로그 저장
    log_path = ROOT / "logs" / "pipeline_log.jsonl"
    log_path.parent.mkdir(exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(log, ensure_ascii=False) + "\n")

    return log


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GoldenBough 무한동력 파이프라인")
    parser.add_argument("--llm", action="store_true", help="외부 LLM 사용")
    parser.add_argument("--provider", default=None, help="LLM 프로바이더 (openai)")
    parser.add_argument("--channels", nargs="+", default=["html", "md", "json"], help="방출 채널")
    parser.add_argument("--simulate-feedback", action="store_true", help="시뮬레이션 반응 주입")
    parser.add_argument("--dynamic-urls", nargs="+", default=[], help="동적 크롤링할 URL")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    dynamic_urls = []
    for u in args.dynamic_urls:
        dynamic_urls.append({"url": u, "name": u.split("/")[2] if "://" in u else u, "category": "web_dynamic", "weight": 1.0})

    run_pipeline(
        use_llm=args.llm,
        llm_provider=args.provider,
        channels=args.channels,
        dynamic_urls=dynamic_urls,
        simulate_feedback=args.simulate_feedback,
        verbose=not args.quiet,
    )
