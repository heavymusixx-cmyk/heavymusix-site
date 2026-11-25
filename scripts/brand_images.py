"""Brand images in the site header's look (Metal Mania lettering, bone "Heavy" + red "Musix", red glow on black).

Run by the "Brand images" workflow (it downloads the free Metal Mania font, SIL Open Font License).
Writes images/brand/: profile.png (1080 square, stacked, fits a round profile crop),
playlist.png (1280 square, for the YouTube Music playlist cover) and banner.png (1500x500).
"""
import os
import sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT = sys.argv[1] if len(sys.argv) > 1 else "MetalMania-Regular.ttf"
BONE, RED, GLOW, BG = (236, 235, 230), (255, 74, 82), (209, 22, 31), (3, 3, 3)


def canvas(w, h):
    im = Image.new("RGB", (w, h), BG)
    # soft red glow in the middle, like the site's header background
    g = Image.new("L", (w, h), 0)
    ImageDraw.Draw(g).ellipse((w * .1, h * .15, w * .9, h * .85), fill=70)
    g = g.filter(ImageFilter.GaussianBlur(min(w, h) * .18))
    im.paste(Image.new("RGB", (w, h), (90, 6, 10)), (0, 0), g)
    return im


def words(im, parts, size, cx, cy, gap=0, maxw=None):
    """parts: list of lines, each a list of (text, color). Centered at (cx, cy); shrinks to fit maxw."""
    d = ImageDraw.Draw(im)
    while True:
        f = ImageFont.truetype(FONT, size)
        widest = max(sum(d.textlength(t, font=f) for t, _ in line) for line in parts)
        if not maxw or widest <= maxw or size < 20:
            break
        size = int(size * .95)
        gap = int(gap * .95)
    lines = []
    for line in parts:
        w = sum(d.textlength(t, font=f) for t, _ in line)
        lines.append((line, w))
    asc, desc = f.getmetrics()
    lh = asc + desc
    total = lh * len(lines) + gap * (len(lines) - 1)
    y0 = cy - total / 2
    glow = Image.new("L", im.size, 0)
    gd = ImageDraw.Draw(glow)
    for i, (line, w) in enumerate(lines):
        x = cx - w / 2
        for t, col in line:
            gd.text((x, y0 + i * (lh + gap)), t, font=f, fill=255)
            x += d.textlength(t, font=f)
    glow = glow.filter(ImageFilter.GaussianBlur(size * .12))
    im.paste(Image.new("RGB", im.size, GLOW), (0, 0), glow.point(lambda v: int(v * .85)))
    for i, (line, w) in enumerate(lines):
        x = cx - w / 2
        y = y0 + i * (lh + gap)
        for t, col in line:
            d.text((x + size * .03, y + size * .03), t, font=f, fill=(0, 0, 0))   # hard shadow
            d.text((x, y), t, font=f, fill=col)
            x += d.textlength(t, font=f)


def small(im, text, size, cx, cy, color=BONE, spacing=.35):
    f = ImageFont.truetype(FONT, size)
    d = ImageDraw.Draw(im)
    chars = list(text)
    w = sum(d.textlength(c, font=f) for c in chars) + size * spacing * (len(chars) - 1)
    x = cx - w / 2
    for c in chars:
        d.text((x, cy - size / 2), c, font=f, fill=color)
        x += d.textlength(c, font=f) + size * spacing


os.makedirs("images/brand", exist_ok=True)
im = canvas(1080, 1080)
words(im, [[("Heavy", BONE)], [("Musix", RED)]], 300, 540, 540, gap=-40, maxw=700)   # stays inside a round crop
im.save("images/brand/profile.png")

im = canvas(1280, 1280)
words(im, [[("Heavy", BONE), ("Musix", RED)]], 250, 640, 600, maxw=1060)
small(im, "RADIO", 90, 640, 800)
im.save("images/brand/playlist.png")

im = canvas(1500, 500)
words(im, [[("Heavy", BONE), ("Musix", RED)]], 230, 750, 230, maxw=1200)
small(im, "EVERY BAND GETS A TURN", 44, 750, 400, spacing=.18)
im.save("images/brand/banner.png")
print("brand images written")
