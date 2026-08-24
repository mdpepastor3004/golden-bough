#!/usr/bin/env python3
"""
황금가지 무한동력 에이전트 v3.0 - 분산 에이전트 오케스트레이터
========================================================
OpenBot 스타일의 분산 에이전트 아키텍처.
각 모듈(ingest, filter, transform, emit, feedback)을 독립적인 서브프로세스로 실행.
병렬 처리 및 격리된 실행 환경 제공.

실행 모드:
- sequential: 순차 실행 (ingest → filter → transform → emit → feedback)
- parallel: filter와 transform 병렬 실행 (emit 전에 동기화)
"""
import json
import os
import sys
import time
import subprocess
import argparse
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = Path(os.environ.get("GOLDEN_BOUGH_ROOT", Path(__file__).parent.parent.resolve()))


def run_module(module_name, args=None, timeout=300):
    """
    단일 모듈을 서브프로세스로 실행하고 JSON 결과를 반환.
    OpenBot 스타일의 격리된 실행 환경.
    """
    if args is None:
        args = []

    cmd = [sys.executable, "-m", module_name] + args
    print(f"🤖 [{module_name}] 실행: {' '.join(cmd)}")

    t0 = time.time()
    try:
        result = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "PYTHONPATH": str(ROOT)}
        )
        duration = time.time() - t0

        if result.returncode != 0:
            print(f"❌ [{module_name}] 실패 (exit code {result.returncode})")
            print(f"   stderr: {result.stderr[:500]}")
            return {
                "stage": module_name,
                "status": "error",
                "error": result.stderr[:1000],
                "duration_sec": round(duration, 2)
            }

        # JSON 출력 파싱 (가장 큰 { ... } 블록을 추출)
        json_output = None
        stdout = result.stdout
        # 모든 { 시작 위치를 찾아 가장 큰 매치를 시도
        candidates = []
        for i, ch in enumerate(stdout):
            if ch == '{':
                candidates.append(i)
        for start in reversed(candidates):
            # 해당 { 부터 끝까지의 부분에서 가장 바깥쪽 } 매칭 (간단: 마지막 } 부터)
            tail = stdout[start:].rstrip()
            # 끝에서부터 가장 빠른 매칭 }를 찾되, brace 카운트로 정확히 매칭
            depth = 0
            end = -1
            for j, ch in enumerate(tail):
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        end = j
                        break
            if end > 0:
                candidate = tail[:end+1]
                try:
                    json_output = json.loads(candidate)
                    break
                except json.JSONDecodeError:
                    continue

        if json_output is None:
            print(f"⚠️  [{module_name}] JSON 파싱 실패, raw 출력 사용")
            json_output = {
                "stage": module_name,
                "status": "warning",
                "raw_output": result.stdout[:2000],
                "duration_sec": round(duration, 2)
            }
        else:
            json_output["duration_sec"] = round(duration, 2)

        print(f"✅ [{module_name}] 완료 ({json_output.get('duration_sec', 0)}초)")
        return json_output

    except subprocess.TimeoutExpired:
        print(f"⏱️  [{module_name}] 타임아웃 ({timeout}초)")
        return {
            "stage": module_name,
            "status": "timeout",
            "error": f"Execution exceeded {timeout}s",
            "duration_sec": timeout
        }
    except Exception as e:
        print(f"❌ [{module_name}] 예외: {e}")
        return {
            "stage": module_name,
            "status": "exception",
            "error": str(e),
            "duration_sec": round(time.time() - t0, 2)
        }


def run_pipeline(mode="sequential", use_llm=False, llm_provider=None, channels=None, simulate_feedback=False, verbose=True):
    """
    전체 파이프라인 실행 (분산 에이전트 오케스트레이션).
    """
    if channels is None:
        channels = ["html", "md", "json"]

    t0 = time.time()
    log = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "stages": {},
        "agents": {}
    }

    print("=" * 60)
    print(f"🏵️  GoldenBough v3.0 - 분산 에이전트 오케스트레이션 ({mode} 모드)")
    print("=" * 60)

    # Stage 1: 흡입
    if verbose:
        print("\n" + "=" * 60)
        print("🤖 Agent 1: 흡입 (Ingest)")
        print("=" * 60)
    ingest_result = run_module("ingest", args=["--parallel"])
    log["agents"]["ingest"] = ingest_result
    log["stages"]["ingest"] = {
        "count": ingest_result.get("count", 0),
        "duration_sec": ingest_result.get("duration_sec", 0)
    }

    if ingest_result.get("status") == "error":
        print("❌ Ingest 실패로 파이프라인 중단")
        return log

    # Stage 2-3: 선별 + 변환
    if mode == "parallel":
        if verbose:
            print("\n" + "=" * 60)
            print("🤖 Agents 2-3: 선별 + 변환 (병렬 실행)")
            print("=" * 60)

        transform_args = []
        if use_llm:
            transform_args.append("--use-llm")
        if llm_provider:
            transform_args.extend(["--llm-provider", llm_provider])

        with ThreadPoolExecutor(max_workers=2) as executor:
            filter_future = executor.submit(run_module, "filter")
            transform_future = executor.submit(run_module, "transform", transform_args)

            filter_result = filter_future.result()
            transform_result = transform_future.result()
    else:
        if verbose:
            print("\n" + "=" * 60)
            print("🤖 Agent 2: 선별 (Filter)")
            print("=" * 60)
        filter_result = run_module("filter")
        log["agents"]["filter"] = filter_result
        log["stages"]["filter"] = {
            "count": filter_result.get("count", 0),
            "duration_sec": filter_result.get("duration_sec", 0)
        }

        if verbose:
            print("\n" + "=" * 60)
            print("🤖 Agent 3: 변환 (Transform)")
            print("=" * 60)
        transform_args = []
        if use_llm:
            transform_args.append("--use-llm")
        if llm_provider:
            transform_args.extend(["--llm-provider", llm_provider])
        transform_result = run_module("transform", args=transform_args)
        log["agents"]["transform"] = transform_result
        log["stages"]["transform"] = {
            "count": transform_result.get("count", 0),
            "duration_sec": transform_result.get("duration_sec", 0)
        }

    if mode == "parallel":
        log["agents"]["filter"] = filter_result
        log["agents"]["transform"] = transform_result
        log["stages"]["filter"] = {
            "count": filter_result.get("count", 0),
            "duration_sec": filter_result.get("duration_sec", 0)
        }
        log["stages"]["transform"] = {
            "count": transform_result.get("count", 0),
            "duration_sec": transform_result.get("duration_sec", 0)
        }

    # Stage 4: 방출
    if verbose:
        print("\n" + "=" * 60)
        print("🤖 Agent 4: 방출 (Emit)")
        print("=" * 60)
    emit_result = run_module("emit", args=["--channels"] + channels)
    log["agents"]["emit"] = emit_result
    log["stages"]["emit"] = {
        "n_cards": emit_result.get("n_cards", 0),
        "channels": list(emit_result.get("emitted", {}).keys()) if isinstance(emit_result.get("emitted"), dict) else [],
        "duration_sec": emit_result.get("duration_sec", 0)
    }

    # Stage 5: 재점화
    if verbose:
        print("\n" + "=" * 60)
        print("🤖 Agent 5: 재점화 (Feedback)")
        print("=" * 60)
    feedback_args = []
    if simulate_feedback:
        feedback_args.append("--simulate-reactions")
    feedback_result = run_module("feedback", args=feedback_args)
    log["agents"]["feedback"] = feedback_result
    log["stages"]["feedback"] = {
        "weights_updated": feedback_result.get("weights_updated", False),
        "duration_sec": feedback_result.get("duration_sec", 0)
    }

    # Stage 6: 한국적 문제해결 자동화 서비스 제안 (Korean Problems Bot)
    if verbose:
        print("\n" + "=" * 60)
        print("🤖 Agent 6: 한국적 문제해결 서비스 제안")
        print("=" * 60)
    korean_result = run_module("korean_problems", args=["--loop"])
    log["agents"]["korean_problems"] = korean_result
    log["stages"]["korean_problems"] = {
        "proposals_generated": korean_result.get("proposals_generated", 0),
        "domains_matched": korean_result.get("domains_matched", {}),
        "duration_sec": korean_result.get("duration_sec", 0)
    }

    # 총평
    log["finished_at"] = datetime.now(timezone.utc).isoformat()
    log["total_duration_sec"] = round(time.time() - t0, 2)

    if verbose:
        print("\n" + "=" * 60)
        print("✅ 파이프라인 완료 (분산 에이전트 오케스트레이션)")
        print("=" * 60)
        print(json.dumps(log, ensure_ascii=False, indent=2))

    # 파이프라인 로그 저장
    log_path = ROOT / "logs" / "pipeline_log.jsonl"
    log_path.parent.mkdir(exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(log, ensure_ascii=False) + "\n")

    return log


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GoldenBough v3.0 분산 에이전트 오케스트레이터")
    parser.add_argument("--mode", choices=["sequential", "parallel"], default="sequential", help="실행 모드")
    parser.add_argument("--llm", action="store_true", help="외부 LLM 사용")
    parser.add_argument("--provider", default=None, help="LLM 프로바이더")
    parser.add_argument("--channels", nargs="+", default=["html", "md", "json"], help="방출 채널")
    parser.add_argument("--simulate-feedback", action="store_true", help="시뮬레이션 반응 주입")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    run_pipeline(
        mode=args.mode,
        use_llm=args.llm,
        llm_provider=args.provider,
        channels=args.channels,
        simulate_feedback=args.simulate_feedback,
        verbose=not args.quiet,
    )
