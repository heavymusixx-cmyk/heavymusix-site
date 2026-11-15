"""Makes a 15-second vertical (1080x1920) social clip for Shorts, Reels, TikTok and Threads.
Usage: python3 scripts/make_clip.py out.mp4 "KICKER" "Headline" "beat one" "beat two" "heavymusix.com/news"
No music (no copyright risk); a silent audio track is included because some apps require one."""
import os, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

out, kicker, headline, b1, b2, link = sys.argv[1:7]
W, H, FPS, SECS = 1080, 1920, 30, 15
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOLD = os.path.join(ROOT, "assets", "fonts", "Poppins-Bold.ttf")
BONE, RED, HOT, INK = (244, 236, 220), (163, 18, 27), (209, 22, 31), (8, 8, 8)
f = lambda s: ImageFont.truetype(BOLD, s)


def wrap(d, text, font, width):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= width:
            cur = t
        else:
            lines.append(cur); cur = w
    return lines + [cur]


def ease(x):
    x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3


bg = Image.new("RGB", (W, H), INK)
gd = ImageDraw.Draw(bg)
for y in range(H):  # red glow from the top
    gd.line([(0, y), (W, y)], fill=(int(8 + 110 * max(0, 1 - y / 900)), 8, 10))

tmp = tempfile.mkdtemp()
for i in range(FPS * SECS):
    t = i / FPS
    im = bg.copy(); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 150], fill=RED)
    d.text((60, 42), "HEAVYMUSIX", font=f(64), fill=BONE)
    d.text((W - 60, 62), "RADIO", font=f(40), fill=BONE, anchor="ra")
    if t < 9.5:  # headline scene, words appear one by one
        d.text((60, 260), kicker.upper(), font=f(44), fill=HOT)
        size = 92
        while size > 56:
            lines = wrap(d, headline, f(size), W - 120)
            if len(lines) * size * 1.15 < 760: break
            size -= 6
        words_shown = int(ease(t / 2.2) * len(headline.split()) + 0.999)
        shown, y = 0, 340
        for ln in lines:
            ws = ln.split(); part = " ".join(ws[:max(0, words_shown - shown)]); shown += len(ws)
            d.text((60, y), part, font=f(size), fill=BONE); y += size * 1.15
        for k, (beat, start) in enumerate(((b1, 3.0), (b2, 5.5))):  # two fact cards slide in
            a = ease((t - start) / 0.6)
            if a <= 0 or not beat: continue
            top = 1180 + k * 300; x = int(60 - (1 - a) * 900)
            d.rectangle([x, top, x + W - 120, top + 250], fill=(20, 18, 18), outline=BONE, width=4)
            d.rectangle([x, top, x + 18, top + 250], fill=HOT)
            yy = top + 30
            for ln in wrap(d, beat, f(44), W - 220)[:3]:
                d.text((x + 50, yy), ln, font=f(44), fill=BONE); yy += 58
    else:  # end card
        a = ease((t - 9.5) / 0.8)
        d.text((W // 2, 640), "Full story", font=f(70), fill=BONE, anchor="mm")
        d.text((W // 2, 760), link, font=f(int(56 + 8 * a)), fill=HOT, anchor="mm")
        d.text((W // 2, 980), "Underground + heavy hitters.", font=f(48), fill=BONE, anchor="mm")
        d.text((W // 2, 1060), "Free radio, daily metal news.", font=f(48), fill=BONE, anchor="mm")
        d.text((W // 2, 1300), "Every band gets a turn.", font=f(60), fill=HOT, anchor="mm")
    d.rectangle([0, H - 14, int(W * (t / SECS)), H], fill=HOT)  # progress bar
    im.save(f"{tmp}/f{i:04d}.png")

subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{tmp}/f%04d.png",
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", out], check=True)
print("made", out)
