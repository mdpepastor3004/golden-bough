#!/usr/bin/env python3
"""
한국적 문제 도메인별 RSS/API 소스 레지스트리.
ingest 모듈에 동적으로 주입되어 사용됨.
"""
KOREAN_SOURCES = [
    # 부동산
    {"name": "네이버 부동산 뉴스", "url": "https://news.naver.com/main/list.naver?mode=LS2D&mid=shm&sid2=260&sid1=101", "kind": "web", "category": "realestate", "weight": 1.5},
    {"name": "정부청약정보", "url": "https://www.applyhome.co.kr/", "kind": "web", "category": "realestate", "weight": 1.2},
    # 취업
    {"name": "사람인 뉴스", "url": "https://www.saramin.co.kr/zf_user/news", "kind": "web", "category": "jobs", "weight": 1.3},
    {"name": "잡코리아", "url": "https://www.jobkorea.co.kr/", "kind": "web", "category": "jobs", "weight": 1.2},
    # 자격증
    {"name": "한국산업인력공단", "url": "https://www.hrdkorea.or.kr/", "kind": "web", "category": "certifications", "weight": 1.4},
    # 창업/정부지원
    {"name": "정책브리핑", "url": "https://www.korea.kr/news/policyFocusList.do", "kind": "web", "category": "government", "weight": 1.5},
    {"name": "K-Startup", "url": "https://www.k-startup.go.kr/", "kind": "web", "category": "startups", "weight": 1.4},
    {"name": "창업넷", "url": "https://www.creativekorea.or.kr/", "kind": "web", "category": "startups", "weight": 1.3},
    # 정부
    {"name": "복지로", "url": "https://www.bokjiro.go.kr/", "kind": "web", "category": "government", "weight": 1.3},
    {"name": "청년정책", "url": "https://www.youthcenter.go.kr/", "kind": "web", "category": "government", "weight": 1.2},
]
