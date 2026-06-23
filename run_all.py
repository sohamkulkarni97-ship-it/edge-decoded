"""
DECODE — content build (no publishing).

fetch -> Sonnet pick+write -> render. Produces output/today_post.json and
output/slide_XX.png. The workflow runs this, commits output/, then runs
publish.py separately (so the images exist at public URLs before posting).

Usage:
  python run_all.py
"""
import fetch
import pick_and_write
import render


def main():
    cands = fetch.fetch_candidates()
    if not cands:
        raise SystemExit("No fresh candidates today.")
    print(f"Fetched {len(cands)} candidates.")
    post = pick_and_write.generate_post(cands, avoid_lanes=pick_and_write._recent_lanes())
    print(f"Chosen [{post.get('lane')}] (score {post.get('score')}): {post.get('chosen_title')}")
    import json
    import os
    out = os.path.join(pick_and_write.HERE, "output", "today_post.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(post, fh, indent=2, ensure_ascii=False)
    paths = render.render_post(post)
    print(f"Rendered {len(paths)} slides.")


if __name__ == "__main__":
    main()
