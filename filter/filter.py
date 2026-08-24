#!/usr/bin/env python3
"""
황금가지 무한동력 에이전트 - 선별 장치 (Filter Module)
========================================================
역할: 흡입된 raw 데이터에서 노이즈를 제거하고 가치 있는 신호만 통과시킨다.
처리:
  1. 중복 제거 (id + URL + 본문 해시)
  2. 언어/길이 필터 (너무 짧거나, 명백한 광고/스팸)
  3. 가치 스코어링 (가중치 + 길이 + 키워드 + 카테고리)
  4. 노이즈 키워드 차단
  5. 클러스터링 (선택) - 유사 콘텐츠 묶기
저장: curated/YYYY-MM-DD/curated_HHMMSS.jsonl
"""
import json
import os
import re
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter
import math

ROOT = Path(os.environ.get("GOLDEN_BOUGH_ROOT", Path(__file__).parent.parent.resolve()))
RAW_DIR = ROOT / "data" / "raw"
CURATED_DIR = ROOT / "data" / "curated"
CURATED_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# 1. 차단 키워드 / 저품질 패턴
# ============================================================
NOISE_PATTERNS = [
    r"\b(sponsored|promoted|advertisement)\b",
    r"쿠폰.*할인",
    r"성인.*채팅",
    r"\b(casino|betting|gambling)\b",
    r"\[removed\]",
    r"\[deleted\]",
]

NOISE_REGEX = re.compile("|".join(NOISE_PATTERNS), re.IGNORECASE)

# 가치 가산 키워드 (카테고리별)
VALUE_KEYWORDS = {
    "ai": ["llm", "gpt", "agent", "rag", "transformer", "fine-tuning", "alignment", "multimodal", "inference", "benchmark", "openai", "anthropic", "claude", "gemini", "llama", "mistral"],
    "research": ["arxiv", "paper", "study", "result", "method", "experiment", "dataset", "benchmark", "sota", "state-of-the-art", "novel"],
    "tech": ["kubernetes", "rust", "python", "typescript", "react", "performance", "scaling", "distributed", "open-source", "github"],
    "code": ["github", "repository", "library", "framework", "release", "v\d+\.\d+", "open source"],
    "finance": ["btc", "eth", "usd", "krw", "price", "market", "exchange"],
    "infra": ["outage", "incident", "degradation", "operational", "latency"],
}

LANG_ASCII_RATIO_MIN = 0.5
MIN_TEXT_LEN = 50  # 본문이 50자 미만이면 버림


# ============================================================
# 2. 중복 제거
# ============================================================
def _content_hash(item):
    """URL 또는 본문으로부터 안정적 해시 생성."""
    for key in ("url", "title"):
        v = item.get(key, "")
        if v:
            return hashlib.sha256(v.strip().lower().encode()).hexdigest()[:16]
    raw = item.get("raw") or item.get("text") or item.get("summary") or ""
    if isinstance(raw, dict):
        raw = json.dumps(raw, sort_keys=True)
    return hashlib.sha256(str(raw).encode()).hexdigest()[:16]


def dedupe(items):
    """id 또는 content hash 기준으로 중복 제거."""
    seen_id = set()
    seen_ch = set()
    out = []
    for it in items:
        iid = it.get("id", "")
        ch = _content_hash(it)
        if iid in seen_id or ch in seen_ch:
            continue
        seen_id.add(iid)
        seen_ch.add(ch)
        it["_dedupe_key"] = ch
        out.append(it)
    return out


# ============================================================
# 3. 노이즈 차단
# ============================================================
def denoise(items):
    out = []
    for it in items:
        text = (it.get("text") or it.get("summary") or it.get("title") or "").lower()
        if not text:
            raw = it.get("raw")
            if isinstance(raw, dict):
                text = json.dumps(raw, ensure_ascii=False).lower()
            elif raw is not None:
                text = str(raw).lower()
        if len(text) < MIN_TEXT_LEN and not it.get("url"):
            continue
        if NOISE_REGEX.search(text):
            continue
        out.append(it)
    return out


# ============================================================
# 4. 가치 스코어링
# ============================================================
def score_value(item):
    """0~100 사이 가치 점수. 높을수록 좋다."""
    score = 0.0
    cat = item.get("category", "general")
    weight = float(item.get("weight", 1.0))

    # 1) 소스 가중치 (5~30점)
    score += min(weight * 15, 30)

    # 2) 본문 길이 (5~20점)
    text = item.get("text") or item.get("summary") or item.get("title") or ""
    raw = item.get("raw")
    if not text and isinstance(raw, dict):
        text = json.dumps(raw, ensure_ascii=False)
    elif not text and raw is not None:
        text = str(raw)
    L = len(text)
    if L > 2000:
        score += 20
    elif L > 800:
        score += 15
    elif L > 300:
        score += 10
    elif L > 100:
        score += 5

    # 3) 카테고리 키워드 매칭 (가산)
    kws = VALUE_KEYWORDS.get(cat, [])
    text_l = text.lower()
    hit = sum(1 for k in kws if k in text_l)
    score += min(hit * 3, 20)

    # 4) URL 패턴 (깊이 있는 글일 가능성)
    url = item.get("url", "")
    if url:
        depth = url.count("/") - 2  # 2 = https://
        if depth >= 2:
            score += 5
        if any(domain in url for domain in ["arxiv.org", "github.com", "anthropic.com", "deepmind.google", "openai.com"]):
            score += 8

    # 5) 시간 보정 (최근일수록 +)
    pub = item.get("published", "")
    if pub and ("T" in pub or pub.endswith(("Z", "+00:00"))):
        score += 3

    item["_value_score"] = round(min(score, 100), 2)
    return item


# ============================================================
# 5. 카테고리별 클러스터링 (간이 - 트리밍)
# ============================================================
def cluster_by_source(items, max_per_source=8):
    """소스별로 상위 N개만 남긴다 (다양성 확보)."""
    by_src = {}
    for it in items:
        by_src.setdefault(it["source"], []).append(it)
    out = []
    for src, lst in by_src.items():
        lst.sort(key=lambda x: x.get("_value_score", 0), reverse=True)
        out.extend(lst[:max_per_source])
    return out


# ============================================================
# 메인
# ============================================================
def run_once(raw_path=None, value_threshold=20.0, max_per_source=8):
    """1회 선별 사이클."""
    if raw_path is None:
        # 가장 최근 raw jsonl 자동 선택
        candidates = sorted(RAW_DIR.glob("*/*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            print("No raw data found.")
            return []
        raw_path = candidates[0]

    items = []
    with open(raw_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))

    n0 = len(items)
    items = dedupe(items)
    n1 = len(items)
    items = denoise(items)
    n2 = len(items)
    for it in items:
        score_value(it)
    items = cluster_by_source(items, max_per_source=max_per_source)
    n3 = len(items)
    items.sort(key=lambda x: x.get("_value_score", 0), reverse=True)
    # 임계치 이하 제거
    items = [it for it in items if it.get("_value_score", 0) >= value_threshold]
    n4 = len(items)

    # 저장
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir = CURATED_DIR / today
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%H%M%S")
    out_path = out_dir / f"curated_{ts}.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

    summary = {
        "input": n0,
        "after_dedupe": n1,
        "after_denoise": n2,
        "after_cluster": n3,
        "after_threshold": n4,
        "saved_to": str(out_path),
        "top5": [
            {"title": it.get("title", "")[:80], "source": it.get("source", ""), "score": it.get("_value_score", 0)}
            for it in items[:5]
        ],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return items


if __name__ == "__main__":
    import sys
    raw = sys.argv[1] if len(sys.argv) > 1 else None
    run_once(raw)
