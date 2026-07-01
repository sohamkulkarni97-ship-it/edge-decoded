"""
DECODE — Instagram publisher (Graph API, official + ban-safe).

Posts the rendered slides as a carousel using the Instagram Content Publishing
API. Images must already be at PUBLIC URLs (the GitHub Actions workflow commits
output/ to the repo, so we use raw.githubusercontent.com URLs).

Carousel flow:
  1) create an image container per slide  (is_carousel_item=true)
  2) create the carousel container        (media_type=CAROUSEL, children, caption)
  3) publish the carousel container

Env required:
  IG_USER_ID        Instagram Business account ID
  IG_ACCESS_TOKEN   long-lived access token
  IMAGE_BASE_URL    public base URL for slide_XX.png (no trailing slash)
Optional:
  DRY_RUN=1         validate URLs + build containers' inputs, do not publish

Usage:
  python publish.py
"""
import datetime as dt
import json
import os
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
POST = os.path.join(HERE, "output", "today_post.json")
POSTED_LOG = os.path.join(HERE, "posted.json")
GRAPH = "https://graph.instagram.com/v21.0"


def _env(name):
    v = os.environ.get(name)
    if not v:
        raise SystemExit(f"Missing required env var: {name}")
    return v


def _post(path, params):
    r = requests.post(f"{GRAPH}/{path}", data=params, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f"Graph API error {r.status_code}: {r.text}")
    return r.json()


def _slide_urls(base, n):
    return [f"{base}/slide_{i:02d}.png" for i in range(1, n + 1)]


def _check_public(url):
    r = requests.head(url, timeout=30, allow_redirects=True)
    if r.status_code >= 400:
        raise RuntimeError(f"Image not publicly reachable ({r.status_code}): {url}")


def _log_posted(post, media_id):
    log = []
    if os.path.exists(POSTED_LOG):
        with open(POSTED_LOG, encoding="utf-8") as fh:
            log = json.load(fh)
    log.append({
        "key": "".join(c for c in post.get("chosen_title", "").lower() if c.isalnum())[:60],
        "lane": post.get("lane"),
        "title": post.get("chosen_title"),
        "media_id": media_id,
        "date": dt.date.today().isoformat(),
    })
    with open(POSTED_LOG, "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=2, ensure_ascii=False)


def publish():
    with open(POST, encoding="utf-8") as fh:
        post = json.load(fh)
    n = len(post["slides"])
    base = _env("IMAGE_BASE_URL").rstrip("/")
    urls = _slide_urls(base, n)

    print(f"Checking {n} images are public under {base} ...")
    for u in urls:
        _check_public(u)
    print("All images reachable.")

    if os.environ.get("DRY_RUN") == "1":
        print("DRY_RUN=1 — would post carousel with these images:")
        for u in urls:
            print("  ", u)
        print("Caption:\n", post["caption"])
        return

    ig = _env("IG_USER_ID")
    token = _env("IG_ACCESS_TOKEN")

    # Give GitHub CDN time to propagate fresh commit before Instagram fetches images
    print("Waiting 90s for CDN propagation...")
    time.sleep(90)

    child_ids = []
    for u in urls:
        for attempt in range(1, 4):
            try:
                res = _post(f"{ig}/media", {
                    "image_url": u, "is_carousel_item": "true", "access_token": token,
                })
                child_ids.append(res["id"])
                print(f"  container {res['id']} <- {u}")
                break
            except RuntimeError as e:
                if attempt == 3:
                    raise
                print(f"  [retry {attempt}/3] container creation failed: {e}")
                time.sleep(15 * attempt)

    carousel = _post(f"{ig}/media", {
        "media_type": "CAROUSEL",
        "children": ",".join(child_ids),
        "caption": post["caption"],
        "access_token": token,
    })
    cid = carousel["id"]

    # carousel containers need a moment to finish processing children
    time.sleep(15)
    for attempt in range(1, 4):
        try:
            published = _post(f"{ig}/media_publish", {
                "creation_id": cid, "access_token": token,
            })
            break
        except RuntimeError as e:
            if attempt == 3:
                raise
            print(f"  [retry {attempt}/3] media_publish failed: {e}")
            time.sleep(30 * attempt)

    media_id = published["id"]
    print(f"PUBLISHED. media_id={media_id}")
    _log_posted(post, media_id)
    return media_id


def refresh_token():
    """Refresh a long-lived Instagram token (run monthly). Prints the new token."""
    token = _env("IG_ACCESS_TOKEN")
    r = requests.get("https://graph.instagram.com/refresh_access_token", params={
        "grant_type": "ig_refresh_token",
        "access_token": token,
    }, timeout=60)
    r.raise_for_status()
    print(r.json().get("access_token", ""))


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "refresh":
        refresh_token()
    else:
        publish()
