"""Generate Edge Decoded brand assets: profile pics + Facebook cover."""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ANTON = os.path.join(HERE, "fonts", "Anton-Regular.ttf")
INTER = os.path.join(HERE, "fonts", "Inter-Variable.ttf")
OUT = os.path.join(HERE, "assets")
BG = (10, 10, 10)
LIME = (200, 255, 0)
WHITE = (255, 255, 255)
INK = (10, 10, 10)


def anton(size):
    return ImageFont.truetype(ANTON, size)


def inter(size, weight=700):
    f = ImageFont.truetype(INTER, size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


def center_line(draw, parts, cx, y, font, tracking=0):
    """Draw [(text,color),...] as one line centered on cx at top-y."""
    widths = [draw.textlength(t, font=font) + tracking * max(len(t) - 1, 0) for t, _ in parts]
    x = cx - sum(widths) / 2
    for (t, c), w in zip(parts, widths):
        xx = x
        for ch in t:
            draw.text((xx, y), ch, font=font, fill=c)
            xx += draw.textlength(ch, font=font) + tracking
        x += w


# ---- profile pictures (1080x1080) -------------------------------------------
def pfp(name, bg, parts, ring=None, size=560):
    S = 1080
    img = Image.new("RGB", (S, S), bg)
    d = ImageDraw.Draw(img)
    if ring:
        d.ellipse([44, 44, S - 44, S - 44], outline=ring, width=18)
    f = anton(size)
    bbox = d.textbbox((0, 0), "E", font=f)
    h = bbox[3] - bbox[1]
    center_line(d, parts, S / 2, (S - h) / 2 - bbox[1], f)
    p = os.path.join(OUT, name)
    img.save(p)
    return p


# ---- Facebook cover (1640x624, mobile-safe centered lockup) ------------------
def cover(name):
    W, H = 1640, 624
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    cx = W / 2
    big = anton(150)
    center_line(d, [("EDGE", WHITE)], cx, 150, big, tracking=4)
    center_line(d, [("DECODED", LIME), (".", WHITE)], cx, 300, big, tracking=4)
    # accent rule
    d.line([(cx - 230, 488), (cx + 230, 488)], fill=(38, 38, 38), width=3)
    tag = inter(34, 600)
    center_line(d, [("THE DAY'S BIGGEST STORY, DECODED DAILY", (150, 150, 150))],
                cx, 512, tag, tracking=4)
    p = os.path.join(OUT, name)
    img.save(p)
    return p


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    # Primary: black bg, "ED" white, "." lime
    main = pfp("pfp_main.png", BG, [("ED", WHITE), (".", LIME)], size=520)
    cov = cover("facebook_cover.png")
    print("wrote pfp_main.png + facebook_cover.png")
