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
# while being eye-catching enough to stop the scroll.
STYLE = (
    "Bold punchy editorial CARTOON illustration with comic-book energy and personality. "
    "Thick clean black outlines, flat vibrant colors, acid-lime green (#C8FF00) as the "
    "DOMINANT accent alongside white and a couple of bold pop colors. Expressive, slightly "
    "exaggerated and funny characters; dynamic composition. Fully TRANSPARENT "
    "background (the art will sit on a black canvas). One focused character or mini-scene. "
    "Absolutely NO text, letters, numbers, speech-bubble words, watermark, or border. Scene: "
)


def generate(art_prompt, out_path, size="1024x1024", quality="medium"):
    client = OpenAI()
    res = client.images.generate(
        model=MODEL,
        prompt=STYLE + art_prompt,
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
