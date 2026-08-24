#!/usr/bin/env python3
"""
korean_problems/registry.py
============================
황금가지 원칙 기반 한국적 문제해결 자동화 서비스 제안 데이터 루프.

각 도메인(realestate, jobs, certifications, startups, government, trends)은
하나의 '봇'으로 등록되며, OpenBot의 AG-UI 프로토콜처럼 다음을 수행:
1. 도메인별 한국적 문제 정의
2. 데이터 흡입 시 해당 문제에 부합하는지 자동 분류
3. 자동화된 가치 제안(서비스) 매칭
4. 수익화 모델 + 기술스택 자동 추천
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("GOLDEN_BOUGH_ROOT", Path(__file__).parent.parent.resolve()))
REGISTRY_DIR = ROOT / "korean_problems"
DATA_DIR = ROOT / "data" / "korean_problems"


# ============================================================
# 한국적 문제 도메인 + 자동화 서비스 제안 매핑
# ============================================================
DOMAINS = {
    "realestate": {
        "label": "부동산",
        "icon": "🏠",
        "pain_points": [
            "청년층 부동산 정보 비대칭",
            "갭투자/영끌 위험성 판단 어려움",
            "전세사기 예방 정보 부족",
            "LH/SH 등 공공임대 대기 순위 관리",
            "재개발/재건축 진행 상황 추적"
        ],
        "service_proposals": [
            {
                "name": "청약가드 (CheongYakGuard)",
                "description": "청약 공고 자동 수집 + 당첨 확률 시뮬레이션 + 알림",
                "stack": ["Python", "Playwright", "텔레그램 봇"],
                "monetization": "월 9,900원 구독 / 기업용 API"
            },
            {
                "name": "전세방패 (JeonseShield)",
                "description": "등기부등본 자동 분석 + 전세사기 위험도 점수",
                "stack": ["FastAPI", "OpenAI", "Supabase"],
                "monetization": "1회 3,000원 / 월 19,000원 무제한"
            }
        ]
    },
    "jobs": {
        "label": "취업/직업",
        "icon": "💼",
        "pain_points": [
            "NCS/자소서 작성 부담",
            "이력서/포트폴리오 관리 분산",
            "비정규직·계약직 불안정",
            "6관정복 같은 다중 자격증 트래킹 어려움",
            "AI 대체 위험 직종 정보 부족"
        ],
        "service_proposals": [
            {
                "name": "자소서 닥터 (CoverLetter Doctor)",
                "description": "공고 자동 파싱 + 맞춤 자소서 초안 + 첨삭",
                "stack": ["LangChain", "Streamlit", "GPT-4o-mini"],
                "monetization": "월 14,900원 / 기업 B2B 라이선스"
            },
            {
                "name": "6관정복 코치",
                "description": "다중 자격증 시험 일정/교재/모임 통합 관리",
                "stack": ["Next.js", "Supabase", "텔레그램 봇"],
                "monetization": "월 7,900원 / 스터디그룹 매칭 수수료"
            }
        ]
    },
    "certifications": {
        "label": "자격증/시험",
        "icon": "📜",
        "pain_points": [
            "응시자격 법규정 빈번 변경",
            "교재 선택/학습법 불확실",
            "시험일정/접수 마감 추적 어려움",
            "합격 후 경력 카운트 관리",
            "1급/2급/기술사 등급별 응시 전략"
        ],
        "service_proposals": [
            {
                "name": "자격증 트래커",
                "description": "관심 자격증 응시자격·시험일·합격률 통합 알림",
                "stack": ["Python", "cron", "텔레그램 봇"],
                "monetization": "월 4,900원 / 공인중개사 등 프리미엄 9,900원"
            }
        ]
    },
    "startups": {
        "label": "창업/1인사업",
        "icon": "🚀",
        "pain_points": [
            "정부지원사업 공고 폭증 →筛选 어려움",
            "양재AI센터/디캠프 등 입주 정보 분산",
            "창업자 마인드셋 + 실행력 부족",
            "세무/노무 자동화 부재",
            "1인 기업 B2B 영업 어려움"
        ],
        "service_proposals": [
            {
                "name": "창업 캘린더 (Founder Calendar)",
                "description": "정부지원사업·입주모집·해커톤 자동 큐레이션",
                "stack": ["RSS", "Python", "Beehiiv"],
                "monetization": "월 19,900원 / 멘토 매칭 50%"
            },
            {
                "name": "1인사업 세무 봇",
                "description": "세금계산서·지출증빙 자동 분류 + 신고 알림",
                "stack": ["FastAPI", "OCR", "GPT-4o"],
                "monetization": "월 29,900원 / 세무사 연결 시 10%"
            }
        ]
    },
    "government": {
        "label": "정부정책/지원금",
        "icon": "🏛️",
        "pain_points": [
            "청년정책/복지 혜택 비대칭 정보",
            "지자체별 상이한 지원 요건",
            "신청 기한·서류 누락",
            "정책 변화 추적 어려움",
            "민원 처리 진행 상황 불투명"
        ],
        "service_proposals": [
            {
                "name": "복지 파인더 (WelfareFinder)",
                "description": "사용자 조건 기반 지원금 자동 매칭 + 알림",
                "stack": ["Next.js", "PostgreSQL", "GPT-4o-mini"],
                "monetization": "무료(B2C) / 지자체 B2G 5,000만원/년"
            }
        ]
    },
    "trends": {
        "label": "트렌드/문화",
        "icon": "📈",
        "pain_points": [
            "Z세대 소비 트렌드 변화 속도",
            "K-콘텐츠 수출 동향 추적",
            "주식/코인 개인 투자자 정보 과부하",
            "MZ세대 워라밸 라이프스타일 수요",
            "인플루언서 마케팅 ROI 측정"
        ],
        "service_proposals": [
            {
                "name": "트렌드 레이더 (TrendRadar)",
                "description": "실시간 SNS/뉴스/검색 트렌드 큐레이션 + 인사이트",
                "stack": ["RSS", "Twitter API", "Streamlit"],
                "monetization": "월 24,900원 / 기업 리서치 100만원/건"
            }
        ]
    }
}


def list_domains():
    """등록된 모든 도메인 봇 목록."""
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
    """텍스트가 어느 도메인에 부합하는지 휴리스틱 분류."""
    keywords = {
        "realestate": ["부동산", "전세", "월세", "청약", "LH", "재개발", "아파트", "매매", "갭투자", "영끌", "SH", "임대주택", "원룸"],
        "jobs": ["취업", "구인", "자소서", "이력서", "면접", "NCS", "비정규직", "계약직", "연봉", "퇴사", "이직", "입사"],
        "certifications": ["자격증", "시험", "응시", "합격", "기사", "기술사", "1급", "2급", "소방안전관리자", "공인중개사", "변리사"],
        "startups": ["창업", "1인기업", "사업자등록", "양재AI센터", "지원사업", "정부지원", "해커톤", "IR", "MVP", "SaaS"],
        "government": ["정부", "정책", "지원금", "복지", "청년정책", "지자체", "민원", "보조금", "국고", "예산"],
        "trends": ["트렌드", "Z세대", "MZ세대", "인플루언서", "K-콘텐츠", "수출", "라이프스타일", "워라밸"]
    }
    scores = {k: 0 for k in keywords}
    for domain, kws in keywords.items():
        for kw in kws:
            if kw in text:
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
    # 가장 부합하는 service_proposal 매칭 (간단히 첫 번째)
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
    for pain in pain_points:
        # 간단한 키워드 매칭
        keywords = pain.split()
        if any(kw in text for kw in keywords if len(kw) > 1):
            return pain
    return pain_points[0]


def run_proposal_loop():
    """
    메인 루프: 최근 curated 데이터 → 도메인 분류 → 서비스 제안 생성 → 저장.
    """
    from filter.filter import run_once as filter_run
    from transform.transform import run_once as transform_run

    # 1) 데이터 선별 + 변환
    curated = filter_run()
    cards = transform_run()

    if not cards:
        return {"status": "no_data", "proposals": []}

    # 2) 도메인별 분류 + 제안 생성
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

    # 3) 저장
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir = DATA_DIR / today
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / "proposals.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        for p in proposals:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    # 4) 도메인별 통계
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
    parser = argparse.ArgumentParser(description="한국적 문제해결 자동화 서비스 제안 봇")
    parser.add_argument("--list", action="store_true", help="등록된 도메인 봇 목록")
    parser.add_argument("--loop", action="store_true", help="제안 루프 실행")
    args = parser.parse_args()

    if args.list:
        print(json.dumps(list_domains(), ensure_ascii=False, indent=2))
    elif args.loop:
        result = run_proposal_loop()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # 기본: 도메인 목록 + 첫 도메인 예시
        domains = list_domains()
        print("🏵️ 황금가지 한국적 문제해결 봇 레지스트리")
        print("=" * 50)
        for d in domains:
            print(f"  {d['icon']} {d['label']} ({d['key']}) — {d['proposal_count']}개 서비스 제안")
        print()
        print("사용법:")
        print("  python3 -m korean_problems.registry --list    # 전체 봇 목록")
        print("  python3 -m korean_problems.registry --loop    # 제안 루프 실행")
