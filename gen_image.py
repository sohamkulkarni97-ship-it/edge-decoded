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

# Locked house style — keeps every cartoon on-brand regardless of subject.
STYLE = (
    "Flat 2-color vector cartoon illustration in a bold minimalist style. "
    "Use ONLY acid-lime green (#C8FF00) and white, on a fully transparent background. "
    "Thick clean outlines, simple geometric shapes, high contrast, centered single subject. "
    "No gradients, no shadows, no 3D, no background scenery, and absolutely no text, "
    "letters, numbers, or watermarks. Subject: "
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
