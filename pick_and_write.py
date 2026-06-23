"""
DECODE — content engine (Claude Sonnet 4.6).

Takes the fresh candidates from fetch.py, asks Sonnet to (1) score them for
engagement, (2) pick the single best story with topic rotation, and (3) write
a DECODE carousel as slide-JSON that render.py consumes, plus an IG caption.

The model call is isolated in `_call_model()` — swap it for Gemini/Haiku/etc.
without touching the rest of the pipeline.

Env: ANTHROPIC_API_KEY must be set.

Usage:
    python pick_and_write.py     # fetch -> Sonnet -> writes output/today_post.json
"""
import json
import os
import re

import anthropic

import fetch

HERE = os.path.dirname(os.path.abspath(__file__))
POSTED_LOG = os.path.join(HERE, "posted.json")
OUT_POST = os.path.join(HERE, "output", "today_post.json")

MODEL = "claude-sonnet-4-6"
HANDLE = "@decodededge"

SYSTEM = f"""You are the editor of Edge Decoded ({HANDLE}), a daily Instagram
carousel page that explains the single most interesting thing happening in news,
science, pharma, and markets. Your voice: sharp, factual, scroll-stopping. Never hype, never
clickbait that the story can't back up. Always attribute the real source.

You will receive a list of fresh news candidates. Do two jobs:

1) SCORE each candidate 0-100 for Instagram engagement using this rubric:
   - Surprise ("wait, what?") - 30
   - Personal impact (health, money, daily life) - 25
   - Visual potential (a big number, %, or clear image) - 20
   - Shareability (would someone send it to a friend) - 15
   - Timeliness - 10
   Avoid: dry procedural news, partisan politics, anything ambiguous or unverifiable.

2) Pick the SINGLE highest scorer, then build an Edge Decoded carousel for it.

CAROUSEL RULES:
- 5 to 7 slides. Always start with a "cover" and end with a "cta".
- Map the story onto the slide types below. Use a "stat" or "ring" slide ONLY if
  the story has a real, sourced number. Use "bars" only for a real trend/comparison.
  Use "illustration" for abstract stories (pick the closest art key). Use "points"
  for a "why it matters" slide. When unsure, use a "cover"-style big-type beat.
- Highlight ONE punchy word/number per headline via the "highlight" field (it is
  drawn in the lime accent). Keep headlines short - they are set in heavy display type.
- Every factual claim must come from the candidate's title/summary. Do not invent
  numbers. If you state a figure, it must be in the source text.

SLIDE SCHEMA (return only these types and fields):
  cover         : label, headline, highlight, source
  stat          : label, value (e.g. "60%"), caption
  ring          : label, percent (number), big (e.g. "78%"), caption, headline, highlight
  bars          : label, bars (list of 4-6 numbers), barlabel, headline, highlight
  illustration  : label, art, headline, highlight
  points        : label, points (list of 2-4 short strings)
  cta           : headline, highlight
ILLUSTRATION art keys: rocket, pill, heart, flask, globe, bolt
LABELS are short uppercase tags: BREAKING, SCIENCE, PHARMA, MARKETS, THE NUMBER,
WHY IT MATTERS, etc.

OUTPUT: return ONLY a JSON object, no prose, no markdown fences, shaped exactly:
{{
  "chosen_title": "...",
  "lane": "...",
  "source": "...",
  "score": 0,
  "caption": "Instagram caption: 1-2 punchy sentences ending with the source, then 6-10 relevant hashtags.",
  "slides": [ ...slide objects per the schema above... ]
}}
"""


def _recent_lanes(n=3):
    if os.path.exists(POSTED_LOG):
        with open(POSTED_LOG, encoding="utf-8") as fh:
            log = json.load(fh)
        return [e.get("lane") for e in log[-n:]]
    return []


def _call_model(system, user):
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


def _extract_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model output")
    return json.loads(text[start:end + 1])


def generate_post(candidates, avoid_lanes=None):
    avoid_lanes = avoid_lanes or []
    lines = []
    for i, c in enumerate(candidates):
        lines.append(f"[{i}] ({c['lane']}) {c['title']} — {c['source']}\n    {c['summary'][:240]}")
    user = (
        f"Recent lanes already posted (rotate away from these if quality is close): "
        f"{avoid_lanes}\n\nCANDIDATES:\n" + "\n".join(lines)
    )
    raw = _call_model(SYSTEM, user)
    post = _extract_json(raw)
    post["handle"] = HANDLE
    return post


if __name__ == "__main__":
    cands = fetch.fetch_candidates()
    if not cands:
        raise SystemExit("No candidates fetched.")
    print(f"Ranking {len(cands)} candidates with {MODEL}...")
    post = generate_post(cands, avoid_lanes=_recent_lanes())
    os.makedirs(os.path.dirname(OUT_POST), exist_ok=True)
    with open(OUT_POST, "w", encoding="utf-8") as fh:
        json.dump(post, fh, indent=2, ensure_ascii=False)
    print(f"\nCHOSEN [{post.get('lane')}] (score {post.get('score')}): {post.get('chosen_title')}")
    print(f"Slides: {len(post.get('slides', []))}  ->  {OUT_POST}")
    print(f"\nCaption:\n{post.get('caption')}")
