#!/usr/bin/env python3
"""
global_problems/registry.py
=============================
글로벌(영어권) 문제해결 자동화 서비스 제안 봇 레지스트리.
korean_problems의 글로벌 버전 — 황금가지 원칙 동일.

각 도메인은 하나의 '봇'으로 등록되며:
1. 글로벌 문제 정의
2. 데이터 흡입 시 자동 분류
3. 자동화된 가치 제안 매칭
4. 수익화 모델 + 기술스택 추천
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("GOLDEN_BOUGH_ROOT", Path(__file__).parent.parent.resolve()))
DATA_DIR = ROOT / "data" / "global_problems"


# ============================================================
# 글로벌 도메인 + 자동화 서비스 제안 매핑
# ============================================================
DOMAINS = {
    "productivity": {
        "label": "Productivity & Tools",
        "icon": "⚡",
        "pain_points": [
            "Context switching between apps",
            "Meeting overload and low signal",
            "Personal knowledge management fragmentation",
            "Subscription sprawl and cost",
            "Time tracking and prioritization"
        ],
        "service_proposals": [
            {
                "name": "DeepFocus OS",
                "description": "AI-driven single-window work environment with auto-context aggregation",
                "stack": ["Tauri", "Rust", "GPT-4o", "Local LLM"],
                "monetization": "$9.99/mo B2C / $15/user/mo B2B"
            },
            {
                "name": "MeetingMiner",
                "description": "Auto-extract action items, decisions, and blockers from meetings",
                "stack": ["Whisper", "LangChain", "Notion API"],
                "monetization": "$12/user/mo / Enterprise $30k+/yr"
            }
        ]
    },
    "finance": {
        "label": "Personal Finance & Wealth",
        "icon": "💰",
        "pain_points": [
            "Information asymmetry in retail investing",
            "Crypto/tax complexity across jurisdictions",
            "Retirement planning uncertainty",
            "Subscription and recurring cost leaks",
            "Cross-border banking and remittance"
        ],
        "service_proposals": [
            {
                "name": "TaxPilot AI",
                "description": "Cross-border tax optimization + crypto tax automation",
                "stack": ["Python", "Pandas", "GPT-4o", "Plaid API"],
                "monetization": "$19/mo DIY / $99/mo with CPA review"
            },
            {
                "name": "WealthOracle",
                "description": "Personalized portfolio rebalancing with regime detection",
                "stack": ["FastAPI", "PostgreSQL", "Streamlit"],
                "monetization": "0.25% AUM / $500+/yr premium"
            }
        ]
    },
    "health": {
        "label": "Health & Longevity",
        "icon": "🏥",
        "pain_points": [
            "Fragmented health data (Apple Health, Oura, labs)",
            "Generic fitness advice not personalized",
            "Sleep and stress recovery optimization",
            "Supplement and nootropic interaction risks",
            "Preventive care vs reactive treatment"
        ],
        "service_proposals": [
            {
                "name": "BioTwin",
                "description": "Personal health digital twin with biomarker tracking + AI recommendations",
                "stack": ["React Native", "InfluxDB", "ML pipelines"],
                "monetization": "$29/mo / Premium $99/mo with clinician"
            }
        ]
    },
    "creator": {
        "label": "Creator Economy",
        "icon": "🎨",
        "pain_points": [
            "Cross-platform content distribution overhead",
            "Audience analytics fragmented across tools",
            "AI slop detection and content quality",
            "Monetization stack (Patreon, Gumroad, ads) complexity",
            "Burnout and creative block"
        ],
        "service_proposals": [
            {
                "name": "CreatorOS",
                "description": "One dashboard for YouTube/Twitter/TikTok/Newsletter analytics + AI content briefs",
                "stack": ["Next.js", "Supabase", "GPT-4o", "Buffer API"],
                "monetization": "$39/mo / $99/mo agency tier"
            },
            {
                "name": "AntiSlop Shield",
                "description": "Detect AI-generated content and add human fingerprint to your work",
                "stack": ["Python", "CLIP", "Custom embeddings"],
                "monetization": "$5/mo / B2B API $0.01/call"
            }
        ]
    },
    "education": {
        "label": "Education & Skills",
        "icon": "🎓",
        "pain_points": [
            "Online course completion rate ~5%",
            "Skill obsolescence acceleration (AI era)",
            "Credential inflation (degrees vs skills)",
            "Personalized learning path generation",
            "Mentor/peer matching at scale"
        ],
        "service_proposals": [
            {
                "name": "SkillGraph",
                "description": "Personalized upskilling paths based on job market signals + your gaps",
                "stack": ["LangChain", "Neo4j", "FastAPI"],
                "monetization": "$14.99/mo / B2B reskilling $50k/yr/team"
            }
        ]
    },
    "aiops": {
        "label": "AI/ML Infrastructure",
        "icon": "🤖",
        "pain_points": [
            "GPU cost optimization across providers",
            "Model evaluation and regression testing",
            "RAG pipeline debugging and monitoring",
            "Multi-model orchestration complexity",
            "Prompt management at scale"
        ],
        "service_proposals": [
            {
                "name": "ModelRouter",
                "description": "Auto-route requests to cheapest/fastest model meeting quality bar",
                "stack": ["Rust", "LiteLLM", "PostgreSQL"],
                "monetization": "20% savings-share / $5k/mo enterprise"
            },
            {
                "name": "EvalForge",
                "description": "LLM regression testing + golden dataset management",
                "stack": ["Python", "Promptfoo", "DuckDB"],
                "monetization": "$99/mo team / $999/mo enterprise"
            }
        ]
    }
}


def list_domains():
    """등록된 모든 글로벌 도메인 봇 목록."""
    return [
        {
            "key": k,
            "label": v["label"],
            "icon": v["icon"],
            "pain_count": len(v["pain_points"]),
            "proposal_count": len(v["service_proposals"])
        }
        for k, v in DOMAINS.items()
    ]


def get_domain(key):
    """특정 도메인 봇 정의."""
    return DOMAINS.get(key)


def classify_to_domain(text):
    """텍스트가 어느 글로벌 도메인에 부합하는지 휴리스틱 분류."""
    keywords = {
        "productivity": ["productivity", "focus", "meeting", "task", "workflow", "pomodoro", "calendar", "inbox", "context switch", "deep work", "notion", "obsidian", "kanban"],
        "finance": ["investing", "stock", "crypto", "bitcoin", "tax", "portfolio", "dividend", "etf", "401k", "ira", "remittance", "defi", "wealth", "retirement"],
        "health": ["sleep", "fitness", "workout", "diet", "nutrition", "nootropic", "longevity", "wearable", "oura", "whoop", "biomarker", "fasting", "mental health"],
        "creator": ["youtube", "tiktok", "instagram", "newsletter", "creator", "influencer", "monetization", "patreon", "substack", "audience", "viral", "content"],
        "education": ["learning", "course", "udemy", "coursera", "degree", "certification", "skill", "bootcamp", "mentor", "study", "tutoring"],
        "aiops": ["llm", "gpt", "claude", "rag", "embedding", "vector", "gpu", "inference", "fine-tuning", "model", "transformer", "agent", "prompt"]
    }
    text_lower = text.lower()
    scores = {k: 0 for k in keywords}
    for domain, kws in keywords.items():
        for kw in kws:
            if kw in text_lower:
                scores[domain] += 1
    best = max(scores.items(), key=lambda x: x[1])
    if best[1] == 0:
        return None, 0
    return best


def generate_proposal(item, domain_key):
    """특정 인사이트에 대한 서비스 제안 생성."""
    domain = get_domain(domain_key)
    if not domain:
        return None
    proposal = domain["service_proposals"][0]
    return {
        "domain": domain_key,
        "domain_label": domain["label"],
        "icon": domain["icon"],
        "matched_pain": _match_pain(item.get("title", "") + " " + item.get("summary", ""), domain["pain_points"]),
        "service_proposal": proposal,
        "source_item_id": item.get("_dedupe_key"),
        "source_title": item.get("title"),
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


def _match_pain(text, pain_points):
    """가장 부합하는 pain point 찾기."""
    text_lower = text.lower()
    for pain in pain_points:
        keywords = pain.lower().split()
        if any(kw in text_lower for kw in keywords if len(kw) > 3):
            return pain
    return pain_points[0]


def run_proposal_loop():
    """
    메인 루프: 최근 curated 데이터 → 글로벌 도메인 분류 → 서비스 제안 생성 → 저장.
    """
    from filter.filter import run_once as filter_run
    from transform.transform import run_once as transform_run

    curated = filter_run()
    cards = transform_run()

    if not cards:
        return {"status": "no_data", "proposals": []}

    proposals = []
    domain_counts = {}
    for card in cards:
        text = (card.get("title", "") or "") + " " + (card.get("summary", "") or "")
        domain_key, score = classify_to_domain(text)
        if domain_key and score > 0:
            proposal = generate_proposal(card, domain_key)
            if proposal:
                proposals.append(proposal)
                domain_counts[domain_key] = domain_counts.get(domain_key, 0) + 1

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir = DATA_DIR / today
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / "proposals.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        for p in proposals:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    stats = {
        "status": "success",
        "date": today,
        "total_cards": len(cards),
        "proposals_generated": len(proposals),
        "domains_matched": domain_counts,
        "proposal_file": str(out_file.relative_to(ROOT))
    }

    stats_file = out_dir / "stats.json"
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    return stats


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="글로벌 문제해결 자동화 서비스 제안 봇")
    parser.add_argument("--list", action="store_true", help="등록된 도메인 봇 목록")
    parser.add_argument("--loop", action="store_true", help="제안 루프 실행")
    args = parser.parse_args()

    if args.list:
        print(json.dumps(list_domains(), ensure_ascii=False, indent=2))
    elif args.loop:
        result = run_proposal_loop()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        domains = list_domains()
        print("🌍 GoldenBough Global Problem-Solving Bot Registry")
        print("=" * 55)
        for d in domains:
            print(f"  {d['icon']} {d['label']} ({d['key']}) - {d['proposal_count']} service proposals")
        print()
        print("Usage:")
        print("  python3 -m global_problems.registry --list    # all bots")
        print("  python3 -m global_problems.registry --loop    # run proposal loop")
