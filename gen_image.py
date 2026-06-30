"""
DECODE — story-specific cartoon generator (OpenAI gpt-image-1).

Given a short art prompt from the content engine, generates a flat lime+white
cartoon on a transparent background, in the Edge Decoded house style, so it
composites cleanly into a slide's hero zone.

Env: OPENAI_API_KEY must be set.
"""
import base64
import os

from openai import OpenAI

MODEL = "gpt-image-1"

# House style — bold, punchy, characterful; lime-dominant so it stays on-brand
# while being eye-catching enough to stop the scroll. Thick art-direction (not
# just "cartoon") so even a short story prompt yields a premium, dynamic result —
# the same upgrade applied to the X engine's hero-image style.
STYLE = (
    "Award-winning, scroll-stopping editorial CARTOON illustration — think a top-tier "
    "New Yorker or Pixar concept artist, NOT a generic clip-art icon. ART DIRECTION: "
    "one bold, instantly-readable character or mini-scene caught mid-ACTION (not a static "
    "pose) — exaggerated, characterful, a little funny or dramatic depending on the story, "
    "with real comic-book energy: dynamic camera angle, a sense of motion (speed lines, "
    "motion blur, flying debris/objects where it fits), expressive oversized gestures and "
    "faces. RENDERING: thick clean confident black outlines, bold flat vibrant color "
    "fields with the color {accent} as the DOMINANT accent alongside white and one or two "
    "bold pop colors, subtle cel-shading/highlight for depth, crisp and high-detail. "
    "Fully TRANSPARENT background (the art sits on a black canvas) — compose the subject "
    "so it reads instantly even small. Make a bold, unexpected creative choice that makes "
    "the viewer look twice. STRICTLY NO text, letters, numbers, speech-bubble words, "
    "watermark, or border anywhere. THE SCENE: "
)


def generate(art_prompt, out_path, accent_hex="#C8FF00", size="1024x1024", quality="medium"):
    client = OpenAI()
    res = client.images.generate(
        model=MODEL,
        prompt=STYLE.format(accent=accent_hex) + art_prompt,
        size=size,
        quality=quality,
        background="transparent",
        n=1,
    )
    data = base64.b64decode(res.data[0].b64_json)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as fh:
        fh.write(data)
    return out_path


if __name__ == "__main__":
    import sys
    prompt = sys.argv[1] if len(sys.argv) > 1 else "a smiling elderly woman with a glowing speech bubble"
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "gen_test.png")
    generate(prompt, out)
    print("wrote", out)
