#!/usr/bin/env python3
"""
황금가지 무한동력 에이전트 - 흡입 장치 (Ingest Module)
========================================================
역할: 인터넷에서 실시간으로 생성되는 인간+AI 데이터를 흡입한다.
소스: RSS, API, 크롤링(정적/동적)
저장: JSON Lines (날짜별 파티션)
"""
import json
import os
import sys
import time
import hashlib
import html
import re
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

try:
    import feedparser
except ImportError:
    feedparser = None

try:
    import requests
except ImportError:
    requests = None

ROOT = Path(os.environ.get("GOLDEN_BOUGH_ROOT", Path(__file__).parent.parent.resolve()))
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


def _log(level, msg):
    log_path = ROOT / "logs" / f"ingest_{level}.log"
    log_path.parent.mkdir(exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now(timezone.utc).isoformat()}] {msg}")


# ============================================================
# 1. RSS / Atom 피드 흡입기
# ============================================================
class RSSIngestor:
    def __init__(self, sources):
        self.sources = sources

    def fetch(self, timeout=15):
        if feedparser is None:
            _log("warn", "feedparser 미설치 - RSS 스킵")
            return []
        results = []
        for src in self.sources:
            try:
                feed = feedparser.parse(src["url"], agent="GoldenBough/2.0")
                if feed.bozo and not feed.entries:
                    continue
                for entry in feed.entries[:20]:
                    url = entry.get("link", "")
                    if not url:
                        continue
                    item = {
                        "id": hashlib.sha256(url.encode()).hexdigest()[:16],
                        "source": src["name"],
                        "category": src.get("category", "general"),
                        "weight": float(src.get("weight", 1.0)),
                        "title": entry.get("title", "").strip()[:500],
                        "url": url,
                        "summary": entry.get("summary", "")[:1000],
                        "published": entry.get("published", ""),
                        "authors": [a.get("name", "") for a in entry.get("authors", [])],
                        "tags": [t.get("term", "") for t in entry.get("tags", [])],
                        "ingested_at": datetime.now(timezone.utc).isoformat(),
                        "module": "ingest.rss",
                        "kind": "rss_entry",
                    }
                    results.append(item)
            except Exception as e:
                _log("warn", f"RSS fail {src['name']}: {e}")
        return results


# ============================================================
# 2. REST API 흡입기
# ============================================================
class APIIngestor:
    def __init__(self, apis):
        self.apis = apis

    def fetch(self, timeout=15):
        if requests is None:
            _log("warn", "requests 미설치 - API 스킵")
            return []
        results = []
        for api in self.apis:
            try:
                r = requests.get(
                    api["url"],
                    headers=api.get("headers", {"User-Agent": "GoldenBough/2.0"}),
                    timeout=timeout,
                )
                r.raise_for_status()
                data = r.json()
                mapper = api.get("mapper")
                if callable(mapper):
                    items_raw = mapper(data)
                else:
                    items_raw = [data]
                for raw in items_raw[:30]:
                    item = {
                        "id": hashlib.sha256(
                            (api["name"] + json.dumps(raw, sort_keys=True, default=str)[:200]).encode()
                        ).hexdigest()[:16],
                        "source": api["name"],
                        "category": api.get("category", "api"),
                        "weight": float(api.get("weight", 1.0)),
                        "raw": raw if isinstance(raw, (dict, str, int, float)) else str(raw)[:2000],
                        "ingested_at": datetime.now(timezone.utc).isoformat(),
                        "module": "ingest.api",
                        "kind": "api_payload",
                    }
                    results.append(item)
            except Exception as e:
                _log("warn", f"API fail {api['name']}: {e}")
        return results


# ============================================================
# 3. 정적 웹 크롤러
# ============================================================
class StaticCrawler:
    def __init__(self, targets):
        self.targets = targets

    def fetch(self, timeout=15):
        if requests is None:
            return []
        results = []
        for tgt in self.targets:
            try:
                r = requests.get(
                    tgt["url"],
                    headers={"User-Agent": "GoldenBough/2.0 (+research)"},
                    timeout=timeout,
                )
                r.raise_for_status()
                text = re.sub(r"<script[^>]*>.*?</script>", " ", r.text, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r"<[^>]+>", " ", text)
                text = html.unescape(text)
                text = re.sub(r"\s+", " ", text).strip()[:8000]
                m = re.search(r"<title[^>]*>(.*?)</title>", r.text, re.IGNORECASE | re.DOTALL)
                title = html.unescape(m.group(1)).strip()[:500] if m else tgt["url"]
                item = {
                    "id": hashlib.sha256(tgt["url"].encode()).hexdigest()[:16],
                    "source": tgt["name"],
                    "category": tgt.get("category", "web"),
                    "weight": float(tgt.get("weight", 1.0)),
                    "title": title,
                    "url": tgt["url"],
                    "text": text,
                    "ingested_at": datetime.now(timezone.utc).isoformat(),
                    "module": "ingest.crawler_static",
                    "kind": "web_page",
                }
                results.append(item)
            except Exception as e:
                _log("warn", f"Static crawl fail {tgt['name']}: {e}")
        return results


# ============================================================
# 4. 동적 웹 크롤러 (Playwright)
# ============================================================
class DynamicCrawler:
    def __init__(self, targets):
        self.targets = targets
        self._browser = None
        self._pw = None

    def _ensure_browser(self):
        if self._browser:
            return True
        try:
            from playwright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=True)
            return True
        except Exception as e:
            _log("warn", f"Playwright unavailable: {e}")
            return False

    def close(self):
        try:
            if self._browser:
                self._browser.close()
            if self._pw:
                self._pw.stop()
        except Exception:
            pass

    def fetch(self, timeout=30):
        if not self._ensure_browser():
            return []
        results = []
        for tgt in self.targets:
            try:
                page = self._browser.new_page()
                page.set_default_timeout(timeout * 1000)
                page.goto(tgt["url"], wait_until="domcontentloaded")
                time.sleep(2)
                content = page.content()
                text = re.sub(r"<script[^>]*>.*?</script>", " ", content, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r"<[^>]+>", " ", text)
                text = html.unescape(text)
                text = re.sub(r"\s+", " ", text).strip()[:8000]
                item = {
                    "id": hashlib.sha256((tgt["url"] + str(time.time())).encode()).hexdigest()[:16],
                    "source": tgt["name"],
                    "category": tgt.get("category", "web_dynamic"),
                    "weight": float(tgt.get("weight", 1.0)),
                    "url": tgt["url"],
                    "text": text,
                    "ingested_at": datetime.now(timezone.utc).isoformat(),
                    "module": "ingest.crawler_dynamic",
                    "kind": "web_page_dynamic",
                }
                results.append(item)
                page.close()
            except Exception as e:
                _log("warn", f"Dynamic crawl fail {tgt['name']}: {e}")
        return results


# ============================================================
# 유틸
# ============================================================
def save_jsonl(items, prefix="ingest"):
    if not items:
        return None
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir = RAW_DIR / today
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%H%M%S")
    path = out_dir / f"{prefix}_{ts}.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    return str(path)


# ============================================================
# 기본 소스
# ============================================================
DEFAULT_RSS = [
    {"name": "HackerNews", "url": "https://news.ycombinator.com/rss", "category": "tech", "weight": 1.5},
    {"name": "Reddit_MachineLearning", "url": "https://www.reddit.com/r/MachineLearning/.rss", "category": "ai", "weight": 1.5},
    {"name": "Reddit_artificial", "url": "https://www.reddit.com/r/artificial/.rss", "category": "ai", "weight": 1.3},
    {"name": "ArXiv_AI", "url": "http://export.arxiv.org/rss/cs.AI", "category": "research", "weight": 2.0},
    {"name": "ArXiv_CL", "url": "http://export.arxiv.org/rss/cs.CL", "category": "research", "weight": 1.5},
    {"name": "Lobsters", "url": "https://lobste.rs/rss", "category": "tech", "weight": 1.2},
]

DEFAULT_APIS = [
    {
        "name": "OpenAI_Status",
        "url": "https://status.openai.com/api/v2/status.json",
        "category": "infra",
        "weight": 0.8,
        "mapper": lambda d: [{"status": d.get("status", {}).get("description", ""), "indicator": d.get("status", {}).get("indicator", "")}],
    },
    {
        "name": "HackerNews_TopStories",
        "url": "https://hacker-news.firebaseio.com/v0/topstories.json",
        "category": "tech",
        "weight": 1.2,
        "mapper": lambda ids: [{"id": i, "rank": idx + 1} for idx, i in enumerate(ids[:30])],
    },
    {
        "name": "CoinGecko_Bitcoin",
        "url": "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd,krw",
        "category": "finance",
        "weight": 0.7,
    },
]

DEFAULT_STATIC = [
    {"name": "OpenAI_Blog", "url": "https://openai.com/blog", "category": "ai", "weight": 1.4},
    {"name": "DeepMind_Blog", "url": "https://deepmind.google/discover/blog/", "category": "ai", "weight": 1.4},
    {"name": "Anthropic_News", "url": "https://www.anthropic.com/news", "category": "ai", "weight": 1.4},
]


def run_once(config=None, parallel=True):
    config = config or {}
    rss_src = config.get("rss", DEFAULT_RSS)
    api_src = config.get("apis", DEFAULT_APIS)
    static_src = config.get("static", DEFAULT_STATIC)
    dynamic_src = config.get("dynamic", [])

    all_items = []
    t0 = time.time()

    if parallel:
        with ThreadPoolExecutor(max_workers=4) as ex:
            futs = {
                ex.submit(RSSIngestor(rss_src).fetch): "rss",
                ex.submit(APIIngestor(api_src).fetch): "api",
                ex.submit(StaticCrawler(static_src).fetch): "static",
            }
            if dynamic_src:
                futs[ex.submit(DynamicCrawler(dynamic_src).fetch)] = "dynamic"
            for fut in as_completed(futs):
                try:
                    all_items.extend(fut.result())
                except Exception as e:
                    _log("warn", f"Module {futs[fut]} fail: {e}")
    else:
        all_items.extend(RSSIngestor(rss_src).fetch())
        all_items.extend(APIIngestor(api_src).fetch())
        all_items.extend(StaticCrawler(static_src).fetch())
        if dynamic_src:
            all_items.extend(DynamicCrawler(dynamic_src).fetch())

    out = save_jsonl(all_items)
    dur = time.time() - t0
    log_entry = {
        "ingested": len(all_items),
        "saved_to": out,
        "duration_sec": round(dur, 2),
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    _log("info", json.dumps(log_entry, ensure_ascii=False))
    print(json.dumps(log_entry, ensure_ascii=False))
    return all_items


if __name__ == "__main__":
    run_once()
