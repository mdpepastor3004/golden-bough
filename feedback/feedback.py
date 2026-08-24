#!/usr/bin/env python3
"""
황금가지 무한동력 에이전트 - 재점화 장치 (Feedback Module)
========================================================
역할: 방출된 산출물에 대한 반응을 다시 흡입하여 시스템 전체를 최적화한다.
기능:
  1. 카드별 반응 추적 (조회/공유/좋아요/댓글) — feedback/feedback.jsonl
  2. 가중치 재계산 — source별/카테고리별 가중치 업데이트
  3. 자동 A/B 메트릭 — 어떤 제목/키워드가 더 반응 좋았는지
  4. 다음 사이클 ingest config 자동 갱신
저장: data/feedback/
"""
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(os.environ.get("GOLDEN_BOUGH_ROOT", Path(__file__).parent.parent.resolve()))
OUTPUT_DIR = ROOT / "data" / "output"
FEEDBACK_DIR = ROOT / "data" / "feedback"
FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)

LOG_PATH = FEEDBACK_DIR / "feedback.jsonl"
WEIGHTS_PATH = FEEDBACK_DIR / "source_weights.json"


# ============================================================
# 1. 반응 기록
# ============================================================
def record_reaction(card_id, reaction, value=1.0, meta=None):
    """
    reaction: 'view' | 'like' | 'share' | 'click' | 'comment' | 'downvote'
    value: 기본 1.0, 의미에 따라 다르게
    """
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "card_id": card_id,
        "reaction": reaction,
        "value": value,
        "meta": meta or {},
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


# ============================================================
# 2. 가중치 재계산
# ============================================================
def recompute_weights(default_weights=None):
    """
    feedback 로그를 분석해서 source/카테고리별 가중치 동적 조정.
    - like/share/click → +0.1
    - downvote → -0.2
    - comment → +0.05
    """
    if not LOG_PATH.exists():
        return None
    reactions_by_source = defaultdict(lambda: {"like": 0, "share": 0, "click": 0, "downvote": 0, "comment": 0, "view": 0, "total": 0})
    # 카드 ID로 source 매핑 (knowledge/<date>/catalog.jsonl 역참조)
    card_to_source = {}
    for catalog_path in (ROOT / "data" / "knowledge").glob("*/catalog.jsonl"):
        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        c = json.loads(line.strip())
                        cid = c.get("source_id")
                        src = c.get("source_meta", {}).get("source")
                        if cid and src:
                            card_to_source[cid] = src
                    except Exception:
                        pass
        except Exception:
            pass

    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            cid = e.get("card_id")
            src = card_to_source.get(cid, "unknown")
            r = e.get("reaction", "view")
            v = float(e.get("value", 1.0))
            if r in reactions_by_source[src]:
                reactions_by_source[src][r] += v
            reactions_by_source[src]["total"] += v

    weights = default_weights or {
        "HackerNews": 1.5, "HackerNews_TopStories": 1.2, "Reddit_MachineLearning": 1.5,
        "Reddit_artificial": 1.3, "ArXiv_AI": 2.0, "ArXiv_CL": 1.5,
        "Lobsters": 1.2, "OpenAI_Blog": 1.4, "DeepMind_Blog": 1.4, "Anthropic_News": 1.4,
        "OpenAI_Status": 0.8, "CoinGecko_Bitcoin": 0.7,
    }

    new_weights = {}
    for src, base_w in weights.items():
        r = reactions_by_source.get(src, {"like": 0, "share": 0, "click": 0, "downvote": 0, "total": 0})
        # 가중치 공식: base * (1 + (like + share + 0.3*click - 2*downvote) / 50)
        delta = (r["like"] * 1.0 + r["share"] * 1.5 + r["click"] * 0.3 - r["downvote"] * 2.0) / 50.0
        new_w = round(base_w * (1.0 + max(-0.5, min(1.0, delta))), 3)
        new_weights[src] = new_w

    # 가중치 저장
    with open(WEIGHTS_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "reactions_summary": {k: dict(v) for k, v in reactions_by_source.items()},
            "weights": new_weights,
        }, f, ensure_ascii=False, indent=2)

    return new_weights


# ============================================================
# 3. 카드 메트릭 (전환율, 조회수)
# ============================================================
def card_metrics():
    """카드별 반응 집계."""
    if not LOG_PATH.exists():
        return {}
    metrics = defaultdict(lambda: Counter())
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
                cid = e.get("card_id", "?")
                r = e.get("reaction", "view")
                metrics[cid][r] += float(e.get("value", 1.0))
            except Exception:
                pass
    return {k: dict(v) for k, v in metrics.items()}


# ============================================================
# 4. 다음 ingest config 자동 갱신
# ============================================================
def write_next_ingest_config():
    """feedback에서 계산된 가중치를 ingest 설정 파일로 저장."""
    if not WEIGHTS_PATH.exists():
        return None
    data = json.loads(WEIGHTS_PATH.read_text(encoding="utf-8"))
    weights = data.get("weights", {})
    # 기본 ingest 설정 + 동적 가중치
    config = {
        "rss": [
            {"name": "HackerNews", "url": "https://news.ycombinator.com/rss", "category": "tech", "weight": weights.get("HackerNews", 1.5)},
            {"name": "Reddit_MachineLearning", "url": "https://www.reddit.com/r/MachineLearning/.rss", "category": "ai", "weight": weights.get("Reddit_MachineLearning", 1.5)},
            {"name": "Reddit_artificial", "url": "https://www.reddit.com/r/artificial/.rss", "category": "ai", "weight": weights.get("Reddit_artificial", 1.3)},
            {"name": "ArXiv_AI", "url": "http://export.arxiv.org/rss/cs.AI", "category": "research", "weight": weights.get("ArXiv_AI", 2.0)},
            {"name": "ArXiv_CL", "url": "http://export.arxiv.org/rss/cs.CL", "category": "research", "weight": weights.get("ArXiv_CL", 1.5)},
            {"name": "Lobsters", "url": "https://lobste.rs/rss", "category": "tech", "weight": weights.get("Lobsters", 1.2)},
        ],
        "apis": [
            {"name": "OpenAI_Status", "url": "https://status.openai.com/api/v2/status.json", "category": "infra", "weight": weights.get("OpenAI_Status", 0.8),
             "mapper": lambda d: [{"status": d.get("status", {}).get("description", ""), "indicator": d.get("status", {}).get("indicator", "")}]},
            {"name": "HackerNews_TopStories", "url": "https://hacker-news.firebaseio.com/v0/topstories.json", "category": "tech", "weight": weights.get("HackerNews_TopStories", 1.2),
             "mapper": lambda ids: [{"id": i, "rank": idx + 1} for idx, i in enumerate(ids[:30])]},
            {"name": "CoinGecko_Bitcoin", "url": "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd,krw", "category": "finance", "weight": weights.get("CoinGecko_Bitcoin", 0.7)},
        ],
        "static": [
            {"name": "OpenAI_Blog", "url": "https://openai.com/blog", "category": "ai", "weight": weights.get("OpenAI_Blog", 1.4)},
            {"name": "DeepMind_Blog", "url": "https://deepmind.google/discover/blog/", "category": "ai", "weight": weights.get("DeepMind_Blog", 1.4)},
            {"name": "Anthropic_News", "url": "https://www.anthropic.com/news", "category": "ai", "weight": weights.get("Anthropic_News", 1.4)},
        ],
    }
    cfg_path = ROOT / "deploy" / "next_ingest_config.json"
    cfg_path.parent.mkdir(exist_ok=True)
    # mapper는 JSON 직렬화 안되므로 문자열로 표시
    serializable = json.loads(json.dumps(config, default=str))
    cfg_path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(cfg_path)


# ============================================================
# 메인
# ============================================================
def run_once(simulate_reactions=False):
    """
    1회 재점화 사이클.
    simulate_reactions=True면 시뮬레이션 데이터로 가중치 시연.
    """
    if simulate_reactions:
        # 시뮬레이션: ArXiv와 HackerNews에 가짜 호의적 반응 주입
        sim = [
            ("arxiv_demo_1", "like", 5),
            ("arxiv_demo_1", "share", 2),
            ("arxiv_demo_2", "like", 3),
            ("hn_demo_1", "click", 10),
            ("hn_demo_1", "like", 1),
            ("reddit_demo_1", "downvote", 2),
        ]
        for cid, r, v in sim:
            record_reaction(cid, r, value=v)

    weights = recompute_weights()
    cfg_path = write_next_ingest_config()
    metrics = card_metrics()
    summary = {
        "weights": weights,
        "n_cards_with_reaction": len(metrics),
        "next_config": cfg_path,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


if __name__ == "__main__":
    import sys
    sim = "--simulate" in sys.argv
    run_once(simulate_reactions=sim)
