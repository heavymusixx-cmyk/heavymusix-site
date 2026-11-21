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

# 4. Today in metal history has entries (the morning task adds them by about 5 AM)
try:
    hist = open("history.js", encoding="utf-8").read()
    key = now.strftime("%m-%d")
    if now.hour >= 7:
        n = len(re.findall(r"year:\s*\d{4}", hist.split('"' + key + '"', 1)[1].split("]", 1)[0])) if '"' + key + '"' in hist else 0
        (problems if n == 0 else notes).append(f"Today in metal history ({key}) has {n} entr{'y' if n == 1 else 'ies'}.")
except Exception as e:
    problems.append(f"history.js could not be read ({e})")

# 5. Today's social clips were made (the clip robot runs at 6:11 AM)
try:
    ci = json.load(open("clips/info.json", encoding="utf-8"))
    if now.hour >= 8:
        (problems if ci.get("date") != now.date().isoformat() or not ci.get("made") else notes).append(
            f"Social clips last made {ci.get('date')} ({len(ci.get('made', []))} clip(s)).")
except FileNotFoundError:
    notes.append("Social clips: none made yet.")

# 6. Content rules: nothing invites band submissions while they are closed, and share titles match page titles
closed = "Closed until submissions open" in open("submit.html", encoding="utf-8").read()
if closed:
    bad = re.compile(r"submissions (are|now) open\b|send (it|your music|us your music)[^.]{0,40}submit@|"
                     r"email (us )?your (music|band)|submit your music now", re.I)
    hits = set()
    for f in ["news.js", "shows.js", "wire.js"] + glob.glob("*.html") + glob.glob("*/*.html"):
        try:
            txt = open(f, encoding="utf-8").read()
        except FileNotFoundError:
            continue
        for m in bad.finditer(txt):
            hits.add(f"{f}: \"{m.group(0)[:60]}\"")
    if hits:
        problems.append("Site says band submissions are open, but they are closed: " + "; ".join(sorted(hits)[:10]))
    else:
        notes.append("No page invites band submissions early.")
mism = []
for f in glob.glob("*.html"):
    txt = open(f, encoding="utf-8").read()
    t = re.search(r"<title>([^<]*)</title>", txt)
    o = re.search(r'property="og:title" content="([^"]*)"', txt)
    if t and o and t.group(1).strip() != o.group(1).strip():
        mism.append(f"{f} (title \"{t.group(1)}\", share title \"{o.group(1)}\")")
(problems if mism else notes).append("Share titles that don't match the page: " + "; ".join(mism) if mism
                                     else "Every hand-made page's share title matches its page title.")

report = ["# HeavyMusix health check", f"Checked {now.strftime('%Y-%m-%d %H:%M')} Arizona time.", ""]
report += ["## Problems"] + [f"- {p}" for p in problems] + [""] if problems else ["All good."]
report += ["## Details"] + [f"- {n}" for n in notes]
open("health_report.md", "w").write("\n".join(report) + "\n")
print("\n".join(report))
sys.exit(1 if problems else 0)
