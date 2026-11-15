"""Builds today's two vertical social clips (Shorts / Reels / TikTok / Threads):
  clips/news.mp4     today's lead story          clips/history.mp4   today in metal history
and clips/info.json (what was made, when). Run daily by .github/workflows/daily-clips.yml."""
import datetime, json, os, re, subprocess, sys

AZ = datetime.timezone(datetime.timedelta(hours=-7))
now = datetime.datetime.now(AZ)
today, mmdd = now.date().isoformat(), now.strftime("%m-%d")


def js(file, var):
    code = f"eval(require('fs').readFileSync({json.dumps(file)},'utf8')+';process.stdout.write(JSON.stringify({var}))')"
    return json.loads(subprocess.check_output(["node", "-e", code], text=True))


def short(s, n=95):
    s = re.split(r"(?<=[.!?])\s", s.strip())[0]
    return s if len(s) <= n else s[:n - 1].rsplit(" ", 1)[0] + "…"


os.makedirs("clips", exist_ok=True)
info = {"date": today, "made": []}
news = [n for n in js("news.js", "NEWS") if n["date"] == today and n.get("tag") not in ("Site", "Coming soon")]
if news:
    n = news[0]
    body = [p for p in n["text"] if not p.lower().startswith("source:")]
    beats = [short(body[0]), short(body[1]) if len(body) > 1 else ""]
    subprocess.run([sys.executable, "scripts/make_clip.py", "clips/news.mp4", "Metal news", n["title"], *beats, "heavymusix.com/news"], check=True)
    info["made"].append({"file": "news.mp4", "title": n["title"]})
hist = sorted(js("history.js", "HISTORY").get(mmdd, []), key=lambda h: h["year"])
if hist:
    label = now.strftime("%B %-d")
    first = hist[0]
    beats = [f"{h['year']}: {short(h['text'], 80)}" for h in hist[1:3]] or [""]
    subprocess.run([sys.executable, "scripts/make_clip.py", "clips/history.mp4", f"{label} in metal history",
                    f"{first['year']}: {short(first['text'], 110)}", *(beats + [""])[:2], "heavymusix.com/today"], check=True)
    info["made"].append({"file": "history.mp4", "title": f"{label} in metal history"})
json.dump(info, open("clips/info.json", "w"), indent=1)
print(json.dumps(info, indent=1))
