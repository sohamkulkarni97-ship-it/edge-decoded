"""
DECODE — Bold Brutalist carousel renderer.

Turns a slide-spec dict (see sample_post.json) into 1080x1350 PNG slides
plus a contact-sheet preview. No design decisions happen here: every slide is
the same skeleton with swappable text/labels/visuals, so the content engine
only fills slots.

Usage:
    python render.py                       # renders sample_post.json
    python render.py path/to/post.json     # renders a given spec
"""
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

# ---- canvas + brand constants ------------------------------------------------
W, H = 1080, 1350
M = 96                       # outer margin
BG = (10, 10, 10)
LIME = (200, 255, 0)
WHITE = (255, 255, 255)
MUTED = (110, 110, 110)
SUB = (150, 150, 150)
LINE = (38, 38, 38)
INK = (10, 10, 10)          # text on accent

# Daily-rotating accent palettes (bg stays black for brand + legibility).
PALETTES = [
    ("lime",   (200, 255, 0),   "#C8FF00"),
    ("cyan",   (0, 229, 255),   "#00E5FF"),
    ("pink",   (255, 61, 165),  "#FF3DA5"),
    ("orange", (255, 106, 0),   "#FF6A00"),
    ("yellow", (255, 212, 0),   "#FFD400"),
    ("violet", (157, 123, 255), "#9D7BFF"),
]


def pick_palette(seed=None):
    """Deterministic daily rotation; pass a seed to force one."""
    import datetime as _dt
    if seed is None:
        seed = _dt.date.today().toordinal()
    return PALETTES[seed % len(PALETTES)]


def set_accent(rgb):
    global LIME
    LIME = tuple(rgb)

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")
OUT_DIR = os.path.join(HERE, "output")

_ANTON = os.path.join(FONT_DIR, "Anton-Regular.ttf")
_INTER = os.path.join(FONT_DIR, "Inter-Variable.ttf")


def anton(size):
    return ImageFont.truetype(_ANTON, size)


def inter(size, weight=600):
    f = ImageFont.truetype(_INTER, size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


def tw(draw, text, font, tracking=0):
    """Width of text including optional letter-spacing."""
    if not text:
        return 0
    base = draw.textlength(text, font=font)
    return base + tracking * (len(text) - 1)


def draw_tracked(draw, xy, text, font, fill, tracking=0):
    """Draw text with letter-spacing (Anton/Inter look better slightly spaced)."""
    x, y = xy
    if tracking == 0:
        draw.text((x, y), text, font=font, fill=fill)
        return
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking


# ---- shared chrome -----------------------------------------------------------
def draw_label(draw, text, y, style="muted"):
    """Top category label. style='pill' (lime box, cover/cta) or 'muted' (caps)."""
    text = text.upper()
    if style == "pill":
        f = inter(30, 800)
        pad_x, pad_y = 22, 14
        tx = tw(draw, text, f, tracking=2)
        draw.rounded_rectangle(
            [M, y, M + tx + pad_x * 2, y + 30 + pad_y * 2], radius=8, fill=LIME
        )
        draw_tracked(draw, (M + pad_x, y + pad_y), text, f, INK, tracking=2)
    else:
        f = inter(28, 800)
        draw_tracked(draw, (M, y), text, f, MUTED, tracking=5)


def draw_footer(draw, handle, index=None, total=None, source=None):
    """Divider + handle (left) and index or source (right)."""
    y = H - 150
    draw.line([(M, y), (W - M, y)], fill=LINE, width=2)
    fh = inter(30, 800)
    draw.text((M, y + 26), handle, font=fh, fill=WHITE)
    right = None
    if source:
        right = source.upper()
    else:
        try:
            right = f"{int(index):02d} / {int(total):02d}"
        except (TypeError, ValueError):
            right = None
    if right:
        fr = inter(26, 600)
        rx = W - M - tw(draw, right, fr, tracking=3)
        draw_tracked(draw, (rx, y + 30), right, fr, MUTED, tracking=3)


# ---- headline (auto-fit + highlight one phrase in lime) ----------------------
def _wrap(draw, words, font, max_w):
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if tw(draw, trial, font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_headline(draw, text, highlight, box, max_size=132, valign="bottom"):
    """Fit an uppercase Anton headline into `box`, coloring `highlight` words lime."""
    bx, by, bw, bh = box
    text = text.upper().strip()
    hl_words = set()
    if highlight:
        for w in highlight.upper().split():
            hl_words.add(w.strip(",.:;!?"))
    words = text.split()

    size = max_size
    while size > 40:
        font = anton(size)
        lh = int(size * 1.0)
        lines = _wrap(draw, words, font, bw)
        if len(lines) * lh <= bh and all(tw(draw, ln, font) <= bw for ln in lines):
            break
        size -= 4
    font = anton(size)
    lh = int(size * 1.0)
    block_h = len(lines) * lh
    if valign == "bottom":
        y = by + bh - block_h
    elif valign == "center":
        y = by + (bh - block_h) // 2
    else:
        y = by

    space_w = draw.textlength(" ", font=font)
    for ln in lines:
        x = bx
        for word in ln.split():
            color = LIME if word.strip(",.:;!?") in hl_words else WHITE
            draw.text((x, y), word, font=font, fill=color)
            x += draw.textlength(word, font=font) + space_w
        y += lh
    return size


def draw_paragraph(draw, text, box, size=40, fill=WHITE, weight=500,
                   leading=1.36, min_size=24, align="left"):
    """Wrap a body paragraph (Inter) and auto-shrink until it fits the box."""
    bx, by, bw, bh = box
    words = (text or "").split()
    s = size
    while s > min_size:
        font = inter(s, weight)
        lines = _wrap(draw, words, font, bw)
        if len(lines) * int(s * leading) <= bh:
            break
        s -= 2
    font = inter(s, weight)
    lh = int(s * leading)
    lines = _wrap(draw, words, font, bw)
    y = by
    for ln in lines:
        x = bx + (bw - tw(draw, ln, font)) / 2 if align == "center" else bx
        draw.text((x, y), ln, font=font, fill=fill)
        y += lh
    return y


# ---- illustrations (flat black+lime, drawn not AI) ---------------------------
def _illo_rocket(draw, cx, cy, s):
    bw = int(s * 0.34)
    draw.rounded_rectangle([cx - bw // 2, cy - s // 2, cx + bw // 2, cy + s // 3],
                           radius=bw // 2, fill=WHITE)
    draw.polygon([(cx - bw // 2, cy - s // 2 + 6), (cx, cy - s // 2 - s // 4),
                  (cx + bw // 2, cy - s // 2 + 6)], fill=LIME)
    draw.ellipse([cx - 22, cy - s // 6 - 22, cx + 22, cy - s // 6 + 22], fill=INK)
    draw.polygon([(cx - bw // 2, cy + s // 8), (cx - bw // 2 - 34, cy + s // 3 + 20),
                  (cx - bw // 2, cy + s // 4)], fill=LIME)
    draw.polygon([(cx + bw // 2, cy + s // 8), (cx + bw // 2 + 34, cy + s // 3 + 20),
                  (cx + bw // 2, cy + s // 4)], fill=LIME)
    draw.polygon([(cx - 26, cy + s // 3), (cx, cy + s // 2 + 30),
                  (cx + 26, cy + s // 3)], fill=LIME)


def _illo_pill(draw, cx, cy, s):
    w, h = int(s * 0.9), int(s * 0.42)
    x0, y0 = cx - w // 2, cy - h // 2
    draw.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=h // 2, fill=WHITE)
    draw.rounded_rectangle([x0, y0, x0 + w // 2 + h // 2, y0 + h], radius=h // 2, fill=LIME)
    draw.rectangle([x0 + w // 2 - 3, y0, x0 + w // 2 + 3, y0 + h], fill=INK)


def _illo_heart(draw, cx, cy, s):
    r = s // 4
    draw.ellipse([cx - r * 2, cy - r, cx, cy + r], fill=LIME)
    draw.ellipse([cx, cy - r, cx + r * 2, cy + r], fill=LIME)
    draw.polygon([(cx - r * 2 + 6, cy + r // 2), (cx + r * 2 - 6, cy + r // 2),
                  (cx, cy + s // 2)], fill=LIME)


def _illo_flask(draw, cx, cy, s):
    top = cy - s // 2
    draw.line([(cx - s // 6, top), (cx - s // 6, cy - s // 8)], fill=WHITE, width=10)
    draw.line([(cx + s // 6, top), (cx + s // 6, cy - s // 8)], fill=WHITE, width=10)
    draw.polygon([(cx - s // 6, cy - s // 8), (cx + s // 6, cy - s // 8),
                  (cx + s // 2, cy + s // 2), (cx - s // 2, cy + s // 2)],
                 outline=WHITE, width=10)
    draw.polygon([(cx - s // 3, cy + s // 6), (cx + s // 3, cy + s // 6),
                  (cx + s // 2 - 6, cy + s // 2 - 6), (cx - s // 2 + 6, cy + s // 2 - 6)],
                 fill=LIME)


def _illo_globe(draw, cx, cy, s):
    r = s // 2
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=LIME, width=10)
    draw.line([(cx - r, cy), (cx + r, cy)], fill=LIME, width=6)
    draw.ellipse([cx - r // 2, cy - r, cx + r // 2, cy + r], outline=LIME, width=6)
    draw.line([(cx, cy - r), (cx, cy + r)], fill=LIME, width=6)


def _illo_bolt(draw, cx, cy, s):
    draw.polygon([(cx + 6, cy - s // 2), (cx - s // 3, cy + s // 12),
                  (cx - 4, cy + s // 12), (cx - 6, cy + s // 2),
                  (cx + s // 3, cy - s // 12), (cx + 4, cy - s // 12)], fill=LIME)


_ILLOS = {"rocket": _illo_rocket, "pill": _illo_pill, "heart": _illo_heart,
          "flask": _illo_flask, "globe": _illo_globe, "bolt": _illo_bolt}


def _paste_hero(ctx, path, cy=420, box=620):
    """Composite an AI-generated cartoon into the slide's hero zone."""
    im = Image.open(path).convert("RGBA")
    im.thumbnail((box, box))
    x = (W - im.width) // 2
    y = cy - im.height // 2
    ctx["img"].paste(im, (x, y), im)


# ---- slide renderers ---------------------------------------------------------
def slide_cover(draw, s, ctx):
    draw_label(draw, s.get("label", "BREAKING"), M, style="pill")
    img = s.get("image")
    if img and os.path.exists(os.path.join(HERE, img)):
        _paste_hero(ctx, os.path.join(HERE, img), cy=440, box=600)
        hl_box, maxsz = (M, 760, W - 2 * M, 300), 118
    else:
        hl_box, maxsz = (M, 300, W - 2 * M, 720), 140
    draw_headline(draw, s["headline"], s.get("highlight"), hl_box,
                  max_size=maxsz, valign="bottom")
    f = inter(30, 800)
    draw_tracked(draw, (M, H - 250), "SWIPE →", f, LIME, tracking=2)
    draw_footer(draw, ctx["handle"], source=s.get("source"))


def slide_stat(draw, s, ctx):
    draw_label(draw, s.get("label", "THE NUMBER"), M, style="muted")
    big = anton(360)
    draw.text((M - 6, 300), s["value"], font=big, fill=LIME)
    cap = s.get("caption", "")
    fc = inter(46, 600)
    lines = _wrap(draw, cap.split(), fc, W - 2 * M)
    y = 760
    for ln in lines:
        draw.text((M, y), ln, font=fc, fill=WHITE)
        y += 58
    draw_footer(draw, ctx["handle"], s.get("index"), ctx["total"])


def slide_ring(draw, s, ctx):
    draw_label(draw, s.get("label", "DATA"), M, style="muted")
    cx, cy, r = W // 2, 420, 170
    draw.arc([cx - r, cy - r, cx + r, cy + r], 0, 360, fill=LINE, width=42)
    pct = float(s.get("percent", 0))
    draw.arc([cx - r, cy - r, cx + r, cy + r], -90, -90 + pct / 100 * 360,
             fill=LIME, width=42)
    big = anton(130)
    btxt = s.get("big", f"{int(pct)}%")
    draw.text((cx - tw(draw, btxt, big) / 2, cy - 95), btxt, font=big, fill=LIME)
    if s.get("caption"):
        draw_paragraph(draw, s["caption"], (M, cy + r + 28, W - 2 * M, 170),
                       size=34, fill=SUB, align="center")
    if s.get("headline"):
        draw_headline(draw, s["headline"], s.get("highlight"),
                      (M, 880, W - 2 * M, 230), max_size=80, valign="top")
    draw_footer(draw, ctx["handle"], s.get("index"), ctx["total"])


def slide_bars(draw, s, ctx):
    draw_label(draw, s.get("label", "MARKETS"), M, style="muted")
    bars = s.get("bars", [30, 50, 45, 70, 100])
    base_y, top_y = 720, 280
    span = base_y - top_y
    n = len(bars)
    gap = 28
    bw = (W - 2 * M - gap * (n - 1)) // n
    mx = max(bars) or 1
    draw.line([(M, base_y), (W - M, base_y)], fill=LINE, width=3)
    for i, v in enumerate(bars):
        x = M + i * (bw + gap)
        bh = int(span * v / mx)
        color = LIME if i == n - 1 else (51, 51, 51)
        draw.rectangle([x, base_y - bh, x + bw, base_y], fill=color)
    if s.get("barlabel"):
        f = anton(54)
        lx = M + (n - 1) * (bw + gap)
        draw.text((lx, base_y - span - 70), s["barlabel"], font=f, fill=LIME)
    if s.get("headline"):
        draw_headline(draw, s["headline"], s.get("highlight"),
                      (M, 800, W - 2 * M, 320), max_size=104, valign="top")
    draw_footer(draw, ctx["handle"], s.get("index"), ctx["total"])


def slide_illustration(draw, s, ctx):
    draw_label(draw, s.get("label", "SCIENCE"), M, style="muted")
    img = s.get("image")
    if img and os.path.exists(os.path.join(HERE, img)):
        _paste_hero(ctx, os.path.join(HERE, img), cy=420, box=620)
    else:
        _ILLOS.get(s.get("art", "bolt"), _illo_bolt)(draw, W // 2, 420, 300)
    draw_headline(draw, s["headline"], s.get("highlight"),
                  (M, 640, W - 2 * M, 190), max_size=88, valign="top")
    if s.get("body"):
        draw_paragraph(draw, s["body"], (M, 860, W - 2 * M, 300),
                       size=36, fill=(205, 205, 205))
    draw_footer(draw, ctx["handle"], s.get("index"), ctx["total"])


def slide_context(draw, s, ctx):
    draw_label(draw, s.get("label", "THE STORY"), M, style="muted")
    draw_headline(draw, s["headline"], s.get("highlight"),
                  (M, 240, W - 2 * M, 280), max_size=92, valign="top")
    draw_paragraph(draw, s.get("body", ""), (M, 580, W - 2 * M, 520),
                   size=42, fill=(222, 222, 222))
    draw_footer(draw, ctx["handle"], s.get("index"), ctx["total"])


def slide_points(draw, s, ctx):
    draw_label(draw, s.get("label", "WHY IT MATTERS"), M, style="muted")
    pts = s.get("points", [])
    top, avail = 300, 850
    size = 46
    while size > 26:
        fp = inter(size, 500)
        lh = int(size * 1.32)
        gap = int(size * 0.95)
        wrapped = [_wrap(draw, p.split(), fp, W - 2 * M - 76) for p in pts]
        if sum(len(w) * lh + gap for w in wrapped) <= avail:
            break
        size -= 2
    fp = inter(size, 500)
    lh = int(size * 1.32)
    gap = int(size * 0.95)
    fd = anton(int(size * 1.05))
    wrapped = [_wrap(draw, p.split(), fp, W - 2 * M - 76) for p in pts]
    y = top
    for lines in wrapped:
        draw.text((M, y - 6), "—", font=fd, fill=LIME)
        yy = y
        for ln in lines:
            draw.text((M + 76, yy), ln, font=fp, fill=WHITE)
            yy += lh
        y = yy + gap
    draw_footer(draw, ctx["handle"], s.get("index"), ctx["total"])


def slide_cta(draw, s, ctx):
    draw_label(draw, s.get("label", "EDGE DECODED"), M, style="pill")
    draw_headline(draw, s.get("headline", "Follow for the day's biggest story"),
                  s.get("highlight"), (M, 360, W - 2 * M, 560),
                  max_size=120, valign="center")
    f = anton(72)
    draw.text((M, H - 320), ctx["handle"].upper(), font=f, fill=LIME)


_RENDERERS = {
    "cover": slide_cover, "stat": slide_stat, "ring": slide_ring,
    "bars": slide_bars, "illustration": slide_illustration,
    "context": slide_context, "points": slide_points, "cta": slide_cta,
}


# ---- driver ------------------------------------------------------------------
def _infer_type(s, index=None, total=None):
    """Resilience: if the model forgot the 'type' tag, deduce it from the fields."""
    if s.get("type"):
        return s["type"]
    if "source" in s:
        return "cover"
    if "points" in s:
        return "points"
    if "percent" in s:
        return "ring"
    if "bars" in s:
        return "bars"
    if "value" in s:
        return "stat"
    if "art" in s:
        return "illustration"
    if "body" in s:
        return "context"
    if total and index == total:
        return "cta"
    return "cover"


def render_slide(spec, ctx):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    ctx = {**ctx, "img": img}
    stype = _infer_type(spec, spec.get("index"), ctx.get("total"))
    _RENDERERS.get(stype, slide_cover)(draw, spec, ctx)
    return img


def render_post(post, out_dir=OUT_DIR):
    os.makedirs(out_dir, exist_ok=True)
    set_accent(post.get("accent_rgb") or pick_palette()[1])
    handle = post.get("handle", "@decodededge")
    slides = post["slides"]
    ctx = {"handle": handle, "total": len(slides)}
    paths = []
    for i, spec in enumerate(slides, 1):
        spec["index"] = i          # renderer owns numbering; never model-controlled
        img = render_slide(spec, ctx)
        p = os.path.join(out_dir, f"slide_{i:02d}.png")
        img.save(p)
        paths.append(p)
    _contact_sheet(paths, os.path.join(out_dir, "_preview.png"))
    return paths


def _contact_sheet(paths, out):
    scale = 0.28
    tw_, th_ = int(W * scale), int(H * scale)
    gap = 18
    sheet = Image.new("RGB", (len(paths) * (tw_ + gap) + gap, th_ + gap * 2), (24, 24, 24))
    for i, p in enumerate(paths):
        thumb = Image.open(p).resize((tw_, th_))
        sheet.paste(thumb, (gap + i * (tw_ + gap), gap))
    sheet.save(out)


if __name__ == "__main__":
    spec_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "sample_post.json")
    with open(spec_path, encoding="utf-8") as fh:
        post = json.load(fh)
    out = render_post(post)
    print(f"Rendered {len(out)} slides -> {OUT_DIR}")
    print(f"Preview -> {os.path.join(OUT_DIR, '_preview.png')}")
