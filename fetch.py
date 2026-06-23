"""
DECODE — source fetcher.

Pulls recent items from free RSS feeds across the four lanes, normalizes them,
drops anything already posted (via posted.json), and returns a candidate list
for the content engine to rank. No API keys needed.

Usage:
    python fetch.py            # prints a sample of today's candidates
"""
import datetime as dt
import json
import os
import re

import feedparser

HERE = os.path.dirname(os.path.abspath(__file__))
POSTED_LOG = os.path.join(HERE, "posted.json")

# lane -> list of free RSS feeds (no key required)
FEEDS = {
    "finance": [
        "https://www.moneycontrol.com/rss/MCtopnews.xml",
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        "https://www.cnbc.com/id/10000664/device/rss/rss.html",
    ],
    "ai": [
        "https://www.technologyreview.com/feed/",
        "https://venturebeat.com/category/ai/feed/",
        "https://techcrunch.com/tag/artificial-intelligence/feed/",
        "https://www.theverge.com/rss/index.xml",
    ],
    "science": [
        "https://www.sciencedaily.com/rss/top/science.xml",
        "https://www.nature.com/nature.rss",
        "https://www.newscientist.com/feed/home/",
        "https://www.nasa.gov/feed/",
    ],
    "pharma": [
        "https://www.statnews.com/feed/",
        "https://www.fiercepharma.com/rss/xml",
        "https://www.who.int/feeds/entity/mediacentre/news/en/rss.xml",
    ],
    "amazing": [
        "https://www.goodnewsnetwork.org/feed/",
        "https://www.upi.com/rss/Odd_News/",
        "https://www.reddit.com/r/Damnthatsinteresting/top/.rss?t=day",
        "https://www.reddit.com/r/UpliftingNews/top/.rss?t=day",
    ],
}

MAX_AGE_HOURS = 48          # only consider fresh items
PER_FEED = 8                # cap items pulled per feed


def _clean(text):
    text = re.sub(r"<[^>]+>", "", text or "")
    return re.sub(r"\s+", " ", text).strip()


def _load_posted():
    if os.path.exists(POSTED_LOG):
        with open(POSTED_LOG, encoding="utf-8") as fh:
            return {e["key"] for e in json.load(fh)}
    return set()


def _key(title):
    return re.sub(r"[^a-z0-9]+", "", (title or "").lower())[:60]


def fetch_candidates():
    posted = _load_posted()
    now = dt.datetime.now(dt.timezone.utc)
    out, seen = [], set()
    for lane, urls in FEEDS.items():
        for url in urls:
            try:
                feed = feedparser.parse(url)
            except Exception:
                continue
            for entry in feed.entries[:PER_FEED]:
                title = _clean(entry.get("title"))
                if not title:
                    continue
                k = _key(title)
                if k in seen or k in posted:
                    continue
                # freshness filter (skip if no/old date)
                pub = entry.get("published_parsed") or entry.get("updated_parsed")
                if pub:
                    age = (now - dt.datetime(*pub[:6], tzinfo=dt.timezone.utc))
                    if age > dt.timedelta(hours=MAX_AGE_HOURS):
                        continue
                seen.add(k)
                body = ""
                if entry.get("content"):
                    body = entry["content"][0].get("value", "")
                body = body or entry.get("summary", "") or entry.get("description", "")
                out.append({
                    "key": k,
                    "lane": lane,
                    "title": title,
                    "summary": _clean(body)[:1800],
                    "source": (feed.feed.get("title") or url.split("/")[2]),
                    "link": entry.get("link", ""),
                })
    return out


if __name__ == "__main__":
    items = fetch_candidates()
    by_lane = {}
    for it in items:
        by_lane.setdefault(it["lane"], []).append(it)
    print(f"Fetched {len(items)} fresh candidates across {len(by_lane)} lanes\n")
    for lane, lst in by_lane.items():
        print(f"=== {lane.upper()} ({len(lst)}) ===")
        for it in lst[:4]:
            print(f"  • [{it['source']}] {it['title']}")
        print()
