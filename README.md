# 🏵️ 황금가지 무한동력 에이전트 (GoldenBough Infinite Engine v3.0)

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/deps-feedparser%20%7C%20requests%20%7C%20numpy%20%7C%20httpx-green.svg)](requirements.txt)
[![GitHub Pages](https://img.shields.io/badge/Demo-Live-brightgreen.svg)](https://mdpepastor3004.github.io/golden-bough/)
[![GitHub](https://img.shields.io/badge/GitHub-mdpepastor3004%2Fgolden--bough-181717.svg)](https://github.com/mdpepastor3004/golden-bough)
[![v3.0](https://img.shields.io/badge/version-v3.0--distributed--agents-gold.svg)](#)

> **연료**: 인터넷에서 실시간으로 생성되는 인간+AI 산출 데이터  
> **원리**: 흡입 → 선별 → 변환 → 방출 → 재점화 (닫힌 루프)  
> **아키텍처**: OpenBot 스타일 **분산 에이전트 오케스트레이션** (6개 독립 에이전트)  
> **한국 모드**: 황금가지 원칙 기반 **한국적 문제해결 자동화 서비스 제안** 데이터 루프 내장  
> **상태**: ✅ 가동 검증 완료 (134 입력 → 42 카드 → 3채널 방출 → 한국 제안 봇)  
> **License**: Apache 2.0 · **Python 3.10+** · 의존성: feedparser, requests, numpy, httpx  
> **Demo**: <https://mdpepastor3004.github.io/golden-bough/>

---

## ⚡ 1-라인 실행

```bash
bash $GOLDEN_BOUGH_ROOT/deploy/golden_bough.sh once
```

## 📂 구조

```
golden_bough/
├── ingest/ingest.py        ← 흡입 (RSS 6 + API 3 + 정적 3 + 동적 N)
├── filter/filter.py        ← 선별 (중복/노이즈/가치점수/클러스터)
├── transform/transform.py  ← 변환 (TextRank 요약, 키워드, 인사이트카드)
├── emit/emit.py            ← 방출 (HTML 대시보드 / MD 뉴스레터 / JSON API / 텔레그램 / 디스코드)
├── feedback/feedback.py    ← 재점화 (가중치 재계산 → 다음 ingest 설정 반영)
├── deploy/
│   ├── pipeline.py         ← 통합 오케스트레이터
│   ├── golden_bough.sh     ← 셸 컨트롤
│   └── next_ingest_config.json  ← 동적 가중치 기반 다음 흡입 설정
├── data/
│   ├── raw/                ← 원본 흡입 데이터 (날짜 파티션)
│   ├── curated/            ← 선별된 데이터
│   ├── knowledge/          ← 인사이트 카드 + 카탈로그 + 인덱스
│   ├── output/             ← 방출 산출물 (HTML/MD/JSON)
│   └── feedback/           ← 반응 로그 + 가중치
└── logs/                   ← 모든 모듈 로그
```

## 🛠️ 명령어

```bash
# 1회 풀사이클 (흡입→선별→변환→방출→재점화)
bash deploy/golden_bough.sh once

# LLM 활성화 (OPENAI_API_KEY 환경변수 필요)
OPENAI_API_KEY=sk-... bash deploy/golden_bough.sh once-llm

# 모듈별 개별 실행
bash deploy/golden_bough.sh ingest
bash deploy/golden_bough.sh filter
bash deploy/golden_bough.sh transform
bash deploy/golden_bough.sh emit
bash deploy/golden_bough.sh feedback

# 상태 확인
bash deploy/golden_bough.sh status

# 최근 로그
bash deploy/golden_bough.sh log

# 30분마다 자동실행 (cron 등록)
bash deploy/golden_bough.sh install-cron

# 자동실행 해제
bash deploy/golden_bough.sh remove-cron
```

## 🔥 핵심 모듈

### 1. 흡입 (Ingest)
- **RSS**: HackerNews, Reddit (ML/AI), ArXiv (AI/CL), Lobsters
- **API**: OpenAI Status, HackerNews Top30, CoinGecko Bitcoin
- **정적 크롤링**: OpenAI/DeepMind/Anthropic 블로그
- **동적 크롤링** (선택): Playwright (설치 시)
- **저장**: `data/raw/YYYY-MM-DD/ingest_HHMMSS.jsonl`

### 2. 선별 (Filter)
- 중복 제거 (id + content hash)
- 노이즈 패턴 차단 (sponsored, 광고, 스팸)
- 가치 스코어링 (0~100): 소스가중치×15 + 길이 + 카테고리 키워드 + URL 깊이 + 도메인
- 카테고리 키워드: ai/research/tech/code/finance/infra
- 클러스터링: 소스별 상위 N개만
- **저장**: `data/curated/YYYY-MM-DD/curated_HHMMSS.jsonl`

### 3. 변환 (Transform)
- **TextRank 추출 요약** (numpy 기반 PageRank, 의존성 0)
- **키워드 추출** (TF + 불용어 + 중요 단어 가중치)
- **인사이트 카드**: 한 줄 + 핵심 3포인트 + 키워드
- **(선택) LLM 임팩트**: OpenAI/Anthropic API 키 있을 때 보강
- **저장**: `data/knowledge/YYYY-MM-DD/cards_HHMMSS.jsonl` + `catalog.jsonl` + `index.json`

### 4. 방출 (Emit)
- **HTML 대시보드** (`dashboard_YYYY-MM-DD.html`): 다크 테마 + TOP 키워드 + 카드 그리드
- **Markdown 뉴스레터** (`newsletter_YYYY-MM-DD.md`): 카테고리별 그룹
- **JSON API** (`api_YYYY-MM-DD.json`): 메타 + 카드
- **(선택) 텔레그램**: `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` 환경변수
- **(선택) 디스코드**: `DISCORD_WEBHOOK_URL` 환경변수

### 5. 재점화 (Feedback)
- 반응 추적: view/like/share/click/comment/downvote
- **가중치 동적 재계산**: `weight = base * (1 + (like + 1.5*share + 0.3*click - 2*downvote) / 50)`
- 다음 ingest config 자동 갱신 (`deploy/next_ingest_config.json`)
- 시뮬레이션 모드 (`--simulate-feedback`)로 가중치 시연 가능

## 🌐 데이터 흐름

```
┌──────────┐    ┌────────┐    ┌────────────┐    ┌────────┐    ┌────────────┐
│ 인터넷   │ →  │ 흡입    │ →  │ 선별       │ →  │ 변환    │ →  │ 방출        │
│ (RSS/API │    │ Ingest │    │ Filter     │    │Transf. │    │ HTML/MD/   │
│  Web)    │    │        │    │ 중복/점수  │    │ 요약/   │    │ JSON/TG/   │
│          │    │        │    │            │    │ 키워드  │    │ Discord    │
└──────────┘    └────────┘    └────────────┘    └────────┘    └────────────┘
                                                                     │
                                                                     ↓
                                                              ┌─────────────┐
                                                              │  재점화       │
                                                              │  가중치 갱신  │
                                                              │  → 다음 흡입  │
                                                              └─────────────┘
                                                                     │
                                                                     └────────┐
                                                                              ↓
                                                                       (다시 흡입으로)
```

## 📈 검증된 실행 결과 (2026-08-24)

| 단계 | 입력 | 출력 | 시간 |
|---|---|---|---|
| 흡입 | RSS 6 + API 3 + Web 3 | **134** items | 3.91s |
| 선별 | 134 | **42** cards | 0.02s |
| 변환 | 42 | **42** insight cards | 0.05s |
| 방출 | 42 | HTML 54K + MD 37K + JSON 68K | 0.01s |
| 재점화 | 6 reactions | 12 source weights | 0.0s |
| **합계** | - | - | **3.99s** |

## 💰 수익화 루프

1. **방출된 산출물** (뉴스레터/대시보드/API) → 사용자 유입
2. **유입에서 발생하는 반응** (구독/공유/댓글) → 재점화 모듈이 흡입
3. **가중치 갱신** → 다음 사이클에서 더 가치 있는 데이터만 선별
4. **품질 향상** → 광고/구독/API 판매/제휴로 수익화
5. **수익의 일부** → 더 큰 LLM 모델/클라우드 인프라에 재투자
6. **무한 반복**

직접 수익화 경로:
- 📰 유료 뉴스레터 (Beehiiv, Substack)
- 🔌 데이터 API 판매 (RapidAPI)
- 📚 자동 생성 e-book (Gumroad)
- 🎓 커뮤니티 멤버십 (Patreon)
- 🤖 자동 생성 콘텐츠 → SNS 채널 운영 (YouTube/Twitter/Threads)

## 🔑 환경변수 (선택)

| 변수 | 용도 | 비고 |
|---|---|---|
| `OPENAI_API_KEY` | LLM 임팩트 강화 | gpt-4o-mini 사용 |
| `ANTHROPIC_API_KEY` | LLM 임팩트 강화 | claude-3-haiku 사용 |
| `GOOGLE_API_KEY` | LLM 임팩트 강화 | gemini-1.5-flash 사용 |
| `ZAI_API_KEY` | GLM 사용 | (확장) |
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | 텔레그램 발송 | |
| `DISCORD_WEBHOOK_URL` | 디스코드 웹훅 | |

모두 비어있어도 핵심 파이프라인은 정상 동작 (LLM 임팩트만 스킵).

## 🧪 빠른 테스트

```bash
# 1) 환경변수 설정 (선택 — 안 주면 스크립트 위치를 자동 감지)
export GOLDEN_BOUGH_ROOT=/path/to/golden_bough

# 2) 한 사이클 돌려보기
cd $GOLDEN_BOUGH_ROOT  # 또는 저장소 루트
python3 deploy/pipeline.py

# 2) 결과 확인
ls -la data/output/                  # HTML/MD/JSON
cat data/feedback/source_weights.json  # 가중치

# 3) (선택) LLM 임팩트 켜고 다시
OPENAI_API_KEY=sk-... python3 deploy/pipeline.py --llm

# 4) 자동실행 등록
bash deploy/golden_bough.sh install-cron
```

---

## 🆕 v3.0: 분산 에이전트 오케스트레이션 (OpenBot 스타일)

**기존 v2.0** → 단일 `pipeline.py`가 모든 모듈을 import하여 순차 실행  
**v3.0** → 각 모듈이 **독립적인 서브프로세스(에이전트)** 로 실행되며, `deploy/pipeline.py`는 오케스트레이터 역할만 담당

### 6개 독립 에이전트

| # | 에이전트 | 역할 | 실행 방식 |
|---|---------|------|----------|
| 1 | **ingest** | RSS 6 + API 3 + 정적크롤러 3 + 한국 소스 10 = 총 22개 소스 | `python -m ingest` |
| 2 | **filter** | 중복·노이즈 제거 + 0~100 가치 스코어링 | `python -m filter` |
| 3 | **transform** | TextRank 요약 + 키워드 + 인사이트카드 (+ LLM 옵션) | `python -m transform` |
| 4 | **emit** | HTML 대시보드 + MD 뉴스레터 + JSON API | `python -m emit` |
| 5 | **feedback** | 가중치 동적 재계산 → 다음 ingest 설정 갱신 | `python -m feedback` |
| 6 | **korean_problems** 🇰🇷 | 황금가지 원칙 기반 한국적 문제해결 자동화 서비스 제안 | `python -m korean_problems` |

### 실행 모드

```bash
# 순차 실행 (기본)
python3 deploy/pipeline.py --mode sequential

# 병렬 실행 (filter + transform 동시)
python3 deploy/pipeline.py --mode parallel
```

---

## 🇰🇷 황금가지 원칙 기반 한국적 문제해결 데이터 루프

**핵심 통찰:** 한국 정부·대기업·플랫폼은 RSS를 거의 제공하지 않는다.  
→ 한국적 문제(부동산, 취업, 자격증, 창업, 정부지원)를 자동 해결하려면 **자체 크롤러/API 어댑터**가 필수.

**`korean_problems/` 모듈이 이 루프를 자동화:**

```
┌─────────────────────────────────────────────┐
│ 1. 한국 도메인 6종 등록 (봇)                  │
│    - realestate / jobs / certifications /    │
│      startups / government / trends          │
├─────────────────────────────────────────────┤
│ 2. 흡입 시 한국 소스 10개 자동 머지           │
│    (네이버부동산, 사람인, 정책브리핑 등)        │
├─────────────────────────────────────────────┤
│ 3. 변환된 인사이트 → 도메인별 자동 분류       │
│    (키워드 매칭 휴리스틱)                      │
├─────────────────────────────────────────────┤
│ 4. 도메인별 pain point 매칭 +                 │
│    자동화 서비스 제안 자동 생성                │
│    (이름, 설명, 스택, 수익화 모델)            │
├─────────────────────────────────────────────┤
│ 5. JSONL 저장 → 다음 사이클 가중치 갱신      │
│    → 한국 소스 가중치 자동 재조정             │
└─────────────────────────────────────────────┘
```

### 등록된 한국 도메인 봇

```bash
python3 -m korean_problems --list
```

| 도메인 | 라벨 | pain points | 서비스 제안 |
|--------|------|-------------|-------------|
| `realestate` | 🏠 부동산 | 5 | 청약가드, 전세방패 |
| `jobs` | 💼 취업/직업 | 5 | 자소서 닥터, 6관정복 코치 |
| `certifications` | 📜 자격증/시험 | 5 | 자격증 트래커 |
| `startups` | 🚀 창업/1인사업 | 5 | 창업 캘린더, 1인사업 세무 봇 |
| `government` | 🏛️ 정부정책/지원금 | 5 | 복지 파인더 |
| `trends` | 📈 트렌드/문화 | 5 | 트렌드 레이더 |

### 제안 루프 실행

```bash
# 한 번 실행 (최근 curated → 분류 → 제안 생성 → JSONL 저장)
python3 -m korean_problems --loop
```

출력 예시 (`data/korean_problems/YYYY-MM-DD/proposals.jsonl`):

```json
{
  "domain": "realestate",
  "matched_pain": "청년층 부동산 정보 비대칭",
  "service_proposal": {
    "name": "청약가드 (CheongYakGuard)",
    "description": "청약 공고 자동 수집 + 당첨 확률 시뮬레이션 + 알림",
    "stack": ["Python", "Playwright", "텔레그램 봇"],
    "monetization": "월 9,900원 구독 / 기업용 API"
  }
}
```

---

## 🛠️ 각 에이전트 직접 호출 (단독 실행)

```bash
# 1단계만: 데이터 흡입
python3 -m ingest --parallel

# 2단계만: 선별
python3 -m filter

# 3단계만: 변환 (LLM 임팩트 켜기)
python3 -m transform --use-llm --llm-provider openai

# 4단계만: 방출 (채널 지정)
python3 -m emit --channels html md

# 5단계만: 재점화
python3 -m feedback --simulate-reactions

# 6단계만: 한국 문제 제안 봇
python3 -m korean_problems --loop
```

각 에이전트는 **독립 실행 가능**하므로 일부만 디버깅·테스트하기 쉽다.

