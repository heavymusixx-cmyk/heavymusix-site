"""HeavyMusix site health check (runs on GitHub every 6 hours).
Checks that the site is up, every internal link works, and the robots are keeping
news, headlines and the show fresh. Writes health_report.md; exits 1 if anything is wrong."""
import datetime, glob, json, os, random, re, subprocess, sys, urllib.request

SITE = "https://heavymusix.com/"
AZ = datetime.timezone(datetime.timedelta(hours=-7))
now = datetime.datetime.now(AZ)
problems, notes = [], []


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "HeavyMusix-health-check"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read()


# 1. Key pages and a random sample of all pages answer
locs = re.findall(r"<loc>([^<]+)</loc>", open("sitemap.xml", encoding="utf-8").read())
must = [SITE, SITE + "news.html", SITE + "show.html", SITE + "bands.html", SITE + "search.html",
        SITE + "feed.xml", SITE + "sitemap.xml", SITE + "robots.txt", SITE + "radio.js", SITE + "show/episodes.json"]
for url in must + random.sample(locs, min(25, len(locs))):
    try:
        status, _ = get(url)
        if status != 200:
            problems.append(f"{url} answered {status}")
    except Exception as e:
        problems.append(f"{url} did not load ({e})")
notes.append(f"Checked {len(must)} key pages and {min(25, len(locs))} random pages of {len(locs)}.")

# 2. Every internal link on every page points to a real file
broken = set()
for f in glob.glob("*.html") + glob.glob("*/*.html"):
    for href in re.findall(r'href="([^"#:?]+\.html)', open(f, encoding="utf-8").read()):
        if "'" in href or "+" in href or href.startswith("//"):
            continue
        if not os.path.exists(href.lstrip("/")):
            broken.add(f"{f} -> {href}")
if broken:
    problems.append(f"{len(broken)} broken internal link(s): " + "; ".join(sorted(broken)[:15]))
else:
    notes.append("All internal links point to real pages.")

# 3. The robots are keeping things fresh
newest = max(re.findall(r'date:\s*"(\d{4}-\d\d-\d\d)"', open("news.js", encoding="utf-8").read()))
age = (now.date() - datetime.date.fromisoformat(newest)).days
(problems if age > 1 else notes).append(f"Newest HeavyMusix story is from {newest} ({age} day(s) old).")
wire = re.search(r'"updated":\s*"([^"]+)"', open("wire.js", encoding="utf-8").read())
if wire:
    w = datetime.datetime.fromisoformat(wire.group(1))
    hrs = (now - w).total_seconds() / 3600
    (problems if hrs > 10 else notes).append(f"Headlines robot last ran {hrs:.0f} hour(s) ago.")
ep = json.load(open("show/episodes.json", encoding="utf-8")).get("updated", "")
if ep:
    d = (now - datetime.datetime.fromisoformat(ep)).total_seconds() / 3600
    (problems if d > 30 else notes).append(f"Radio Show builder last ran {d:.0f} hour(s) ago.")

report = ["# HeavyMusix health check", f"Checked {now.strftime('%Y-%m-%d %H:%M')} Arizona time.", ""]
report += ["## Problems"] + [f"- {p}" for p in problems] + [""] if problems else ["All good."]
report += ["## Details"] + [f"- {n}" for n in notes]
open("health_report.md", "w").write("\n".join(report) + "\n")
print("\n".join(report))
sys.exit(1 if problems else 0)
