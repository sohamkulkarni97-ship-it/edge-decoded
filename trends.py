"""
DECODE — trending signal layer.

Adds "what is the internet paying attention to right now" on top of the curated
RSS feeds, so the content engine can LIGHTLY favor timely topics without going
off-brand. Two parts:

  trend_signals()       -> a short list of hot terms (Hacker News front page +
                           Wikipedia most-viewed) passed to the model as context.
  trending_candidates() -> real, SOURCED trending articles pulled from Google
                           News on-brand topic feeds (Science / Tech / Health),
                           added to the candidate pool tagged trending=True. Because
                           they carry a real source, the model can write from them
                           without inventing facts.

All sources are free, key-less, and reliable on a headless GitHub Actions runner.
"""
import datetime as dt
import re

import feedparser
import requests

UA = {"User-Agent": "EdgeDecoded/1.0 (+https://x.com/decodededge)"}

# On-brand Google News topic feeds (avoids the politics/sport-heavy top-stories feed).
GOOGLE_NEWS_TOPICS = {
    "science": "https://news.google.com/rss/headlines/section/topic/SCIENCE?hl=en-US&gl=US&ceid=US:en",
    "tech":    "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en",
    "health":  "https://news.google.com/rss/headlines/section/topic/HEALTH?hl=en-US&gl=US&ceid=US:en",
}


def _clean(t):
    t = re.sub(r"<[^>]+>", "", t or "")
    return re.sub(r"\s+", " ", t).strip()


def _key(title):
    return re.sub(r"[^a-z0-9]+", "", (title or "").lower())[:60]


def _hn_titles(limit=12):
    """Hacker News front page (Algolia API) — trending tech/science/AI."""
    try:
        r = requests.get("https://hn.algolia.com/api/v1/search",
                         params={"tags": "front_page", "hitsPerPage": 30}, timeout=20)
        hits = r.json().get("hits", [])
    except Exception:
        return []
    hits = [h for h in hits if (h.get("points") or 0) >= 50 and h.get("title")]
    return [_clean(h["title"]) for h in hits[:limit]]


def _wiki_titles(limit=12):
    """Wikipedia most-viewed articles yesterday — what the world is reading about."""
    day = dt.date.today() - dt.timedelta(days=1)
    url = (f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/"
           f"en.wikipedia/all-access/{day.year}/{day.month:02d}/{day.day:02d}")
    try:
        r = requests.get(url, headers=UA, timeout=20)
        arts = r.json()["items"][0]["articles"]
    except Exception:
        return []
    bad = ("Main_Page", "Special:", "Wikipedia:", "Portal:", "Help:", "Category:",
           "Deaths_in_", "List_of")
    out = []
    for a in arts:
        name = a.get("article", "")
        if not name or any(b in name for b in bad):
            continue
        out.append(name.replace("_", " "))
        if len(out) >= limit:
            break
    return out


def trend_signals():
    """A short, deduped list of hot terms for model context (best-effort)."""
    seen, out = set(), []
    for t in _hn_titles() + _wiki_titles():
        k = _key(t)
        if k and k not in seen:
            seen.add(k)
            out.append(t)
    return out


def trending_candidates(posted, seen, per_topic=5, max_age_hours=48):
    """Sourced trending articles from Google News on-brand topic feeds."""
    now = dt.datetime.now(dt.timezone.utc)
    out = []
    for lane, url in GOOGLE_NEWS_TOPICS.items():
        try:
            feed = feedparser.parse(url)
        except Exception:
            continue
        for e in feed.entries[:per_topic]:
            title = _clean(e.get("title"))
            if not title:
                continue
            k = _key(title)
            if k in seen or k in posted:
                continue
            pub = e.get("published_parsed") or e.get("updated_parsed")
            if pub:
                age = now - dt.datetime(*pub[:6], tzinfo=dt.timezone.utc)
                if age > dt.timedelta(hours=max_age_hours):
                    continue
            seen.add(k)
            summary = _clean(e.get("summary") or e.get("description") or "")
            # Google News titles are "Headline - Source"; split the source out.
            src = title.rsplit(" - ", 1)[-1] if " - " in title else "Google News"
            out.append({
                "key": k, "lane": lane, "title": title,
                "summary": summary[:1800], "source": src,
                "link": e.get("link", ""), "trending": True,
            })
    return out


if __name__ == "__main__":
    print("=== TREND SIGNALS (hot terms) ===")
    for t in trend_signals():
        print("  •", t)
    print("\n=== TRENDING CANDIDATES (sourced) ===")
    for c in trending_candidates(set(), set()):
        print(f"  [{c['lane']}] {c['title']}  ({c['source']})")
