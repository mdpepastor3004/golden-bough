#!/usr/bin/env python3
"""
황금가지 무한동력 에이전트 - 변환로 (Transform Module)
========================================================
역할: 선별된 데이터를 가치 있는 산출물로 변환한다.
산출물 종류:
  1. 요약 (extractive: 핵심 문장 추출)
  2. 키워드/태그 추출
  3. 카테고리 자동 분류
  4. 인사이트 카드 (한 줄 요약 + 3 핵심 포인트)
  5. (선택) LLM 호출 - OpenAI/Anthropic/Google API 키 있을 때
  6. (선택) 임베딩 - sentence-transformers 있으면
저장: data/transformed/YYYY-MM-DD/...
"""
import json
import os
import re
import math
import hashlib
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

import numpy as np

ROOT = Path(os.environ.get("GOLDEN_BOUGH_ROOT", Path(__file__).parent.parent.resolve()))
CURATED_DIR = ROOT / "data" / "curated"
TRANSFORM_DIR = ROOT / "data" / "knowledge"
TRANSFORM_DIR.mkdir(parents=True, exist_ok=True)

try:
    import httpx
except ImportError:
    httpx = None


# ============================================================
# 1. 본문 추출
# ============================================================
def _text_of(item):
    text = item.get("text") or item.get("summary") or item.get("title") or ""
    if not text:
        raw = item.get("raw")
        if isinstance(raw, dict):
            text = json.dumps(raw, ensure_ascii=False)
        elif raw is not None:
            text = str(raw)
    return text.strip()


# ============================================================
# 2. 키워드 추출 (간이 TF + 불용어 제거)
# ============================================================
STOPWORDS = set("""
a an the and or but if then of in on at to for from by with as is are was were be been being have has had do does did this that these those it its their there here what when where which who whom how why not no nor so than too very can will just should would could may might must shall about above after again against all am any because before below between both did down during each few further had has have having he her him his into more most my now off once only other our out over own same some such through under until up upon was were what when where which while who whom why will with you your yours
그리고 또는 그러나 하지만 그래서 따라서 등 등등 이 그 저 것 수 등 매우 아주 정말 그냥 좀 더 잘 못 다시 한번 바로 여기 거기 거 너무 매우 워 진짜 그냥 게 다 그게 이게 그런 이런 저런 우리 나 너 당신 그들 이런 저런 등등
""".split())

# 가중치 1.5배 단어들
IMPORTANT = {"arxiv", "openai", "anthropic", "google", "github", "release", "benchmark", "agent", "llm", "gpt", "claude", "gemini", "transformer", "rag", "fine-tuning", "alignment", "sota", "novel", "paper", "study", "result", "method", "dataset", "performance", "scaling", "distributed", "kubernetes", "rust", "python", "typescript", "react", "framework", "library", "outage", "incident", "operational", "btc", "eth", "usd", "krw", "market", "price"}


def extract_keywords(item, top_k=8):
    text = _text_of(item).lower()
    # 토큰화 (영문 + 숫자 + 한글 2자 이상)
    tokens = re.findall(r"[a-z][a-z0-9_-]{2,}|[\uac00-\ud7af]{2,}", text)
    weights = Counter()
    for t in tokens:
        if t in STOPWORDS:
            continue
        if len(t) < 3:
            continue
        if t in IMPORTANT:
            weights[t] += 1.5
        else:
            weights[t] += 1.0
    return [w for w, _ in weights.most_common(top_k)]


# ============================================================
# 3. 추출 요약 (TextRank 간이 버전)
# ============================================================
def textrank_summarize(text, n_sentences=3, lang="en"):
    """문장 간 co-occurrence 그래프 → PageRank로 상위 n개 추출."""
    if not text or len(text) < 200:
        return [text.strip()] if text.strip() else []

    # 문장 분리
    if lang == "ko":
        sents = re.split(r"(?<=[.!?\n])\s+", text)
    else:
        sents = re.split(r"(?<=[.!?])\s+", text)
    sents = [s.strip() for s in sents if len(s.strip()) > 20]
    if len(sents) <= n_sentences:
        return sents

    # 토큰화
    def tok(s):
        return re.findall(r"[a-z0-9]+|[\uac00-\ud7af]{2,}", s.lower())

    tokenized = [tok(s) for s in sents]
    vocab = {}
    for toks in tokenized:
        for t in toks:
            if t not in vocab:
                vocab[t] = len(vocab)

    N = len(sents)
    # 동시출현 행렬
    M = np.zeros((N, N), dtype=np.float32)
    window = 2
    for i in range(N):
        for j in range(i + 1, N):
            shared = len(set(tokenized[i]) & set(tokenized[j]))
            if shared > 0:
                # 짧은 문장 패널티
                sim = shared / (math.log(len(tokenized[i]) + 1) + math.log(len(tokenized[j]) + 1))
                M[i, j] = sim
                M[j, i] = sim

    # 정규화
    row_sum = M.sum(axis=1)
    row_sum[row_sum == 0] = 1
    M = M / row_sum[:, None]

    # PageRank
    d = 0.85
    scores = np.ones(N, dtype=np.float32) / N
    for _ in range(30):
        new = (1 - d) / N + d * M.T @ scores
        if np.allclose(new, scores, atol=1e-5):
            break
        scores = new

    # 상위 n개
    idx = np.argsort(-scores)[:n_sentences]
    idx = sorted(idx.tolist())
    return [sents[i] for i in idx]


# ============================================================
# 4. 인사이트 카드 생성
# ============================================================
def make_insight_card(item):
    text = _text_of(item)
    keywords = extract_keywords(item, top_k=6)
    summary = textrank_summarize(text, n_sentences=3)
    # 1줄 핵심
    title = item.get("title", "").strip()[:200]
    return {
        "type": "insight_card",
        "id": hashlib.sha256((item.get("id", "") + "insight").encode()).hexdigest()[:16],
        "source_id": item.get("id"),
        "source_meta": {
            "source": item.get("source"),
            "url": item.get("url"),
            "category": item.get("category"),
            "value_score": item.get("_value_score"),
        },
        "title": title,
        "one_liner": (summary[0] if summary else title)[:280],
        "key_points": summary[:3],
        "keywords": keywords,
        "url": item.get("url", ""),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================
# 5. LLM 호출 (선택) - 환경변수에 API 키 있을 때
# ============================================================
def llm_enrich(card, provider=None, timeout=20):
    """외부 LLM으로 한 줄 해석/요약 보강. 키 없으면 원본 그대로 반환."""
    api_key_openai = os.environ.get("OPENAI_API_KEY")
    api_key_anthropic = os.environ.get("ANTHROPIC_API_KEY")
    api_key_google = os.environ.get("GOOGLE_API_KEY")
    api_key_zai = os.environ.get("ZAI_API_KEY")

    # 우선순위: 환경변수
    if provider == "openai" or (not provider and api_key_openai):
        if not httpx or not api_key_openai:
            return card
        try:
            r = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key_openai}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "다음 텍스트를 한국어로 2문장 요약하고 한 줄 임팩트만 출력해."},
                        {"role": "user", "content": (card.get("title", "") + "\n" + " ".join(card.get("key_points", [])))[:2000]},
                    ],
                    "max_tokens": 200,
                    "temperature": 0.3,
                },
                timeout=timeout,
            )
            if r.status_code == 200:
                txt = r.json()["choices"][0]["message"]["content"].strip()
                card["llm_impact"] = txt[:500]
        except Exception as e:
                card["llm_error"] = str(e)[:200]
    return card


# ============================================================
# 6. 메타 카탈로그 (날짜별 통합 인덱스)
# ============================================================
def update_catalog(cards, today=None):
    today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cat_path = TRANSFORM_DIR / today / "catalog.jsonl"
    cat_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cat_path, "a", encoding="utf-8") as f:
        for c in cards:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    # 인덱스 갱신
    idx_path = TRANSFORM_DIR / today / "index.json"
    idx = {"date": today, "count": 0, "by_source": {}, "by_category": {}, "top_keywords": []}
    if idx_path.exists():
        try:
            idx = json.loads(idx_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    idx["count"] += len(cards)
    for c in cards:
        s = c.get("source_meta", {}).get("source", "?")
        idx["by_source"][s] = idx["by_source"].get(s, 0) + 1
        cat = c.get("source_meta", {}).get("category", "?")
        idx["by_category"][cat] = idx["by_category"].get(cat, 0) + 1
    # 키워드 집계
    kw_counter = Counter()
    if idx_path.exists():
        try:
            old = json.loads(idx_path.read_text(encoding="utf-8"))
            for kw, n in old.get("top_keywords", []):
                kw_counter[kw] = n
        except Exception:
            pass
    for c in cards:
        for kw in c.get("keywords", []):
            kw_counter[kw] += 1
    idx["top_keywords"] = kw_counter.most_common(20)
    idx["updated_at"] = datetime.now(timezone.utc).isoformat()
    idx_path.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
    return idx


# ============================================================
# 메인
# ============================================================
def run_once(curated_path=None, use_llm=False, llm_provider=None, max_items=50):
    if curated_path is None:
        cands = sorted(CURATED_DIR.glob("*/*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not cands:
            print("No curated data.")
            return []
        curated_path = cands[0]

    items = []
    with open(curated_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))

    items = items[:max_items]
    cards = []
    for it in items:
        try:
            card = make_insight_card(it)
            if use_llm:
                card = llm_enrich(card, provider=llm_provider)
            cards.append(card)
        except Exception as e:
            print(f"transform fail {it.get('id')}: {e}")

    # 저장
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir = TRANSFORM_DIR / today
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%H%M%S")
    out_path = out_dir / f"cards_{ts}.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for c in cards:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    idx = update_catalog(cards, today=today)

    summary = {
        "input_items": len(items),
        "generated_cards": len(cards),
        "saved_to": str(out_path),
        "catalog": idx,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return cards


if __name__ == "__main__":
    import sys
    use_llm = "--llm" in sys.argv
    provider = None
    if "--provider=openai" in sys.argv:
        provider = "openai"
    curated = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else None
    run_once(curated_path=curated, use_llm=use_llm, llm_provider=provider)
