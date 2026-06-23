"""
DECODE — content build (no publishing).

fetch -> Sonnet pick+write -> generate cartoons -> render. Produces
output/today_post.json and output/slide_XX.png. The workflow runs this, commits
output/, then runs publish.py separately (so images exist at public URLs first).

Usage:
  python run_all.py
"""
import json
import os

import fetch
import pick_and_write
import render

HERE = pick_and_write.HERE


def _add_cartoons(post, accent_hex):
    """For each slide with an art_prompt, generate a cartoon in the day's accent (best-effort)."""
    if not os.environ.get("OPENAI_API_KEY"):
        print("[note] OPENAI_API_KEY not set — using fallback drawn shapes.")
        return
    import gen_image
    for i, sl in enumerate(post["slides"]):
        prompt = sl.get("art_prompt")
        if not prompt:
            continue
        rel = os.path.join("assets", f"gen_{i:02d}.png")
        try:
            gen_image.generate(prompt, os.path.join(HERE, rel), accent_hex=accent_hex)
            sl["image"] = rel
            print(f"  cartoon -> {rel}  ({prompt[:48]}...)")
        except Exception as e:
            print(f"  [warn] cartoon gen failed ({e}); using fallback shape.")


def main():
    cands = fetch.fetch_candidates()
    if not cands:
        raise SystemExit("No fresh candidates today.")
    print(f"Fetched {len(cands)} candidates.")
    post = pick_and_write.generate_post(cands, avoid_lanes=pick_and_write._recent_lanes())
    print(f"Chosen [{post.get('lane')}] (score {post.get('score')}): {post.get('chosen_title')}")
    name, rgb, accent_hex = render.pick_palette()
    post["palette"] = name
    post["accent_rgb"] = list(rgb)
    print(f"Palette: {name} ({accent_hex})")
    _add_cartoons(post, accent_hex)
    out = os.path.join(HERE, "output", "today_post.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(post, fh, indent=2, ensure_ascii=False)
    paths = render.render_post(post)
    print(f"Rendered {len(paths)} slides.")


if __name__ == "__main__":
    main()
