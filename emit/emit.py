#!/usr/bin/env python3
"""
황금가지 무한동력 에이전트 - 방출 장치 (Emit Module)
========================================================
역할: 변환된 카드를 다양한 외부 채널로 내보낸다.
채널:
  1. 로컬 HTML 대시보드 (data/output/dashboard.html)
  2. Markdown 뉴스레터 (data/output/newsletter.md)
  3. JSON API 응답 (data/output/api.json)
  4. (선택) 텔레그램 봇으로 발송 - TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID 환경변수 있을 때
  5. (선택) 디스코드 웹훅 - DISCORD_WEBHOOK_URL
  6. (선택) 노션 / 워드프레스 (확장용 placeholder)
저장: data/output/...
"""
import json
import os
import html
import re
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

try:
    import httpx
except ImportError:
    httpx = None

ROOT = Path(os.environ.get("GOLDEN_BOUGH_ROOT", Path(__file__).parent.parent.resolve()))
KNOWLEDGE_DIR = ROOT / "data" / "knowledge"
OUTPUT_DIR = ROOT / "data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 카드 로드
# ============================================================
def load_cards(today=None, max_cards=50):
    today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cat_path = KNOWLEDGE_DIR / today / "catalog.jsonl"
    if not cat_path.exists():
        return []
    cards = []
    with open(cat_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cards.append(json.loads(line))
    # 중복 제거 (source_id 기반)
    seen = set()
    unique = []
    for c in cards:
        sid = c.get("source_id")
        if sid in seen:
            continue
        seen.add(sid)
        unique.append(c)
    return unique[:max_cards]


# ============================================================
# 1. HTML 대시보드
# ============================================================
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>황금가지 대시보드 - {date}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0a0a0a;color:#e0e0e0;margin:0;padding:24px;line-height:1.6}}
h1{{color:#ffd700;border-bottom:2px solid #ffd700;padding-bottom:8px}}
.kw{{display:inline-block;background:#1e1e1e;border:1px solid #333;padding:4px 10px;margin:3px;border-radius:12px;font-size:13px}}
.kw.hot{{background:#3d2c00;border-color:#ffd700;color:#ffd700}}
.card{{background:#141414;border:1px solid #222;border-left:4px solid #ffd700;border-radius:8px;padding:18px;margin:14px 0}}
.card h2{{margin:0 0 8px 0;color:#fff;font-size:18px}}
.card .meta{{font-size:12px;color:#888;margin-bottom:8px}}
.card .one{{font-style:italic;color:#bbb;margin:8px 0}}
.card ul{{margin:6px 0;padding-left:20px}}
.card li{{margin:4px 0;font-size:14px}}
.card a{{color:#4da6ff;text-decoration:none}}
.card a:hover{{text-decoration:underline}}
.score{{float:right;background:#ffd700;color:#000;padding:2px 8px;border-radius:8px;font-weight:bold;font-size:12px}}
.stats{{display:flex;gap:16px;margin:16px 0;flex-wrap:wrap}}
.stat{{background:#1a1a1a;padding:12px 18px;border-radius:8px;border:1px solid #333}}
.stat .n{{font-size:28px;color:#ffd700;font-weight:bold}}
.stat .l{{font-size:12px;color:#888}}
</style>
</head>
<body>
<h1>🏵️ 황금가지 무한동력 대시보드</h1>
<div class="stats">
<div class="stat"><div class="n">{n_cards}</div><div class="l">카드 수</div></div>
<div class="stat"><div class="n">{n_sources}</div><div class="l">소스 수</div></div>
<div class="stat"><div class="n">{n_categories}</div><div class="l">카테고리 수</div></div>
<div class="stat"><div class="n">{date}</div><div class="l">날짜 (UTC)</div></div>
</div>
<h2>🔥 TOP 키워드</h2>
<div>{keywords_html}</div>
<h2>📰 인사이트 카드</h2>
{cards_html}
</body>
</html>"""


def emit_html(cards, today):
    if not cards:
        return None
    # 통계
    sources = Counter()
    categories = Counter()
    kws = Counter()
    for c in cards:
        sm = c.get("source_meta", {})
        sources[sm.get("source", "?")] += 1
        categories[sm.get("category", "?")] += 1
        for k in c.get("keywords", []):
            kws[k] += 1

    top_kws = kws.most_common(15)
    keywords_html = "".join(
        f'<span class="kw{" hot" if i < 5 else ""}">{html.escape(k)} ×{n}</span>'
        for i, (k, n) in enumerate(top_kws)
    )

    cards_html_parts = []
    for c in cards:
        sm = c.get("source_meta", {})
        title = html.escape(c.get("title", ""))
        one = html.escape(c.get("one_liner", ""))
        pts = c.get("key_points", [])
        url = c.get("url", "")
        score = sm.get("value_score", 0)
        src = html.escape(sm.get("source", ""))
        cat = html.escape(sm.get("category", ""))
        kws_str = " ".join(f'<span class="kw">{html.escape(k)}</span>' for k in c.get("keywords", []))
        pts_html = "".join(f"<li>{html.escape(p[:300])}</li>" for p in pts)
        url_html = f'<a href="{html.escape(url)}" target="_blank">{html.escape(url[:80])}</a>' if url else ""
        llm = c.get("llm_impact", "")
        llm_html = f'<div class="one">🤖 {html.escape(llm)}</div>' if llm else ""
        cards_html_parts.append(
            f'<div class="card"><span class="score">{score}</span>'
            f'<h2>{title}</h2>'
            f'<div class="meta">{src} · {cat} {url_html}</div>'
            f'<div class="one">{one}</div>'
            f'{llm_html}'
            f'<ul>{pts_html}</ul>'
            f'<div>{kws_str}</div>'
            f'</div>'
        )

    html_doc = HTML_TEMPLATE.format(
        date=today,
        n_cards=len(cards),
        n_sources=len(sources),
        n_categories=len(categories),
        keywords_html=keywords_html,
        cards_html="\n".join(cards_html_parts),
    )
    out_path = OUTPUT_DIR / f"dashboard_{today}.html"
    out_path.write_text(html_doc, encoding="utf-8")
    return str(out_path)


# ============================================================
# 2. Markdown 뉴스레터
# ============================================================
def emit_markdown(cards, today):
    if not cards:
        return None
    lines = [
        f"# 🏵️ 황금가지 인사이트 - {today}",
        "",
        f"**{len(cards)}개 카드** | 자동 생성 (GoldenBough v2.0)",
        "",
        "---",
        "",
    ]
    # 카테고리별 그룹
    by_cat = {}
    for c in cards:
        cat = c.get("source_meta", {}).get("category", "general")
        by_cat.setdefault(cat, []).append(c)

    for cat, lst in by_cat.items():
        lines.append(f"## 📂 {cat.upper()} ({len(lst)}개)")
        lines.append("")
        for c in lst:
            title = c.get("title", "")
            url = c.get("url", "")
            score = c.get("source_meta", {}).get("value_score", 0)
            one = c.get("one_liner", "")[:280]
            pts = c.get("key_points", [])
            kws = ", ".join(c.get("keywords", []))
            llm = c.get("llm_impact", "")
            lines.append(f"### {title}")
            if url:
                lines.append(f"🔗 {url}")
            lines.append(f"**점수**: {score} | **키워드**: {kws}")
            lines.append("")
            lines.append(f"> {one}")
            if llm:
                lines.append("")
                lines.append(f"🤖 {llm}")
            if pts:
                lines.append("")
                lines.append("**핵심 포인트:**")
                for p in pts[:3]:
                    lines.append(f"- {p[:280]}")
            lines.append("")
            lines.append("---")
            lines.append("")

    out_path = OUTPUT_DIR / f"newsletter_{today}.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return str(out_path)


# ============================================================
# 3. JSON API
# ============================================================
def emit_json_api(cards, today):
    payload = {
        "meta": {
            "date": today,
            "count": len(cards),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "engine": "GoldenBough v2.0",
        },
        "cards": cards,
    }
    out_path = OUTPUT_DIR / f"api_{today}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(out_path)


# ============================================================
# 4. (선택) 텔레그램
# ============================================================
def emit_telegram(cards, today, max_send=5, timeout=10):
    bot = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not (bot and chat and httpx):
        return None
    if not cards:
        return None
    # 요약 메시지
    header = f"🏵️ *황금가지 인사이트* - {today}\n*총 {len(cards)}개 카드 중 상위 {min(max_send, len(cards))}개*"
    results = []
    try:
        r = httpx.post(
            f"https://api.telegram.org/bot{bot}/sendMessage",
            json={"chat_id": chat, "text": header, "parse_mode": "Markdown", "disable_web_page_preview": True},
            timeout=timeout,
        )
        results.append({"header": r.status_code})
    except Exception as e:
        results.append({"header_error": str(e)[:200]})
    for i, c in enumerate(cards[:max_send], 1):
        sm = c.get("source_meta", {})
        title = c.get("title", "")[:200]
        url = c.get("url", "")
        one = c.get("one_liner", "")[:240]
        score = sm.get("value_score", 0)
        kws = ", ".join(c.get("keywords", [])[:5])
        text = f"*{i}. {title}*\n📊 {score} | 🏷 {kws}\n\n{one}\n\n{url}"
        try:
            r = httpx.post(
                f"https://api.telegram.org/bot{bot}/sendMessage",
                json={"chat_id": chat, "text": text[:4000], "parse_mode": "Markdown", "disable_web_page_preview": True},
                timeout=timeout,
            )
            results.append({f"card_{i}": r.status_code})
        except Exception as e:
            results.append({f"card_{i}_error": str(e)[:200]})
    return results


# ============================================================
# 5. (선택) 디스코드 웹�훅
# ============================================================
def emit_discord(cards, today, max_send=5, timeout=10):
    url_wh = os.environ.get("DISCORD_WEBHOOK_URL")
    if not (url_wh and httpx) or not cards:
        return None
    results = []
    for i, c in enumerate(cards[:max_send], 1):
        sm = c.get("source_meta", {})
        title = c.get("title", "")[:200]
        src_url = c.get("url", "")
        one = c.get("one_liner", "")[:500]
        score = sm.get("value_score", 0)
        embed = {
            "title": title,
            "url": src_url,
            "description": one,
            "color": 0xFFD700,
            "footer": {"text": f"🏵️ GoldenBough · {today} · score {score}"},
        }
        try:
            r = httpx.post(url_wh, json={"embeds": [embed]}, timeout=timeout)
            results.append({f"card_{i}": r.status_code})
        except Exception as e:
            results.append({f"card_{i}_error": str(e)[:200]})
    return results


# ============================================================
# 메인
# ============================================================
def run_once(today=None, channels=None):
    today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    channels = channels or ["html", "md", "json"]
    cards = load_cards(today=today, max_cards=50)
    if not cards:
        print("No cards to emit.")
        return {}

    results = {"date": today, "n_cards": len(cards), "emitted": {}}
    if "html" in channels:
        path = emit_html(cards, today)
        if path:
            results["emitted"]["html"] = path
    if "md" in channels:
        path = emit_markdown(cards, today)
        if path:
            results["emitted"]["markdown"] = path
    if "json" in channels:
        path = emit_json_api(cards, today)
        if path:
            results["emitted"]["json"] = path
    if "telegram" in channels:
        r = emit_telegram(cards, today)
        if r:
            results["emitted"]["telegram"] = r
    if "discord" in channels:
        r = emit_discord(cards, today)
        if r:
            results["emitted"]["discord"] = r
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return results


if __name__ == "__main__":
    import sys
    channels = sys.argv[1:] or ["html", "md", "json"]
    run_once(channels=channels)
