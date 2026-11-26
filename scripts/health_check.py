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
                     r"email (us )?your (music|band)|submit your music now|"
                     r"bands:\s*(<[^>]+>\s*)*submit@|submissions are free[^.]{0,20}submit@", re.I)
    hits = set()
    for f in ["news.js", "shows.js", "wire.js", "scripts/fan_email.py"] + glob.glob("*.html") + glob.glob("*/*.html"):
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

# 7. Code and data files still load (a broken file breaks the site for every visitor)
def node(args):
    try:
        r = subprocess.run(["node"] + args, capture_output=True, text=True, timeout=60)
        return r.returncode, (r.stderr or r.stdout).strip().splitlines()[-1:] or [""]
    except FileNotFoundError:
        return None, ["node not installed"]
bad_code = []
for js in ["radio.js", "skin.js", "hmx.js"]:
    if os.path.exists(js):
        rc, err = node(["--check", js])
        if rc:
            bad_code.append(f"{js}: {err[0]}")
for js, var in [("news.js", "NEWS"), ("shows.js", "SHOWS"), ("history.js", "HISTORY"), ("wire.js", "WIRE")]:
    if os.path.exists(js):
        rc, err = node(["-e", "var window=globalThis;" + f"eval(require('fs').readFileSync('{js}','utf8'));" + f"if(typeof {var}==='undefined')throw Error('{var} missing')"])
        if rc:
            bad_code.append(f"{js}: {err[0]}")
for jf in glob.glob("show/*.json") + glob.glob("clips/*.json") + glob.glob("social/*.json"):
    try:
        json.load(open(jf, encoding="utf-8"))
    except Exception as e:
        bad_code.append(f"{jf}: {e}")
if bad_code:
    problems.append("Files that won't load: " + "; ".join(bad_code))
else:
    notes.append("All scripts and data files load.")

# 8. Wording checks on every page: misspelled band names, and search summaries cut off mid-word
misspell = {r"\bJorn Lande\b": "Jørn Lande", r"\bMotley Crue\b": "Mötley Crüe", r"\bMotorhead\b": "Motörhead",
            r"\bBlue Oyster Cult\b": "Blue Öyster Cult", r"\bQueensryche\b": "Queensrÿche"}
spell = set()
for f in ["news.js", "history.js"] + glob.glob("*.html"):
    txt = open(f, encoding="utf-8").read()
    for pat, right in misspell.items():
        if re.search(pat, txt):
            spell.add(f"{f}: should be {right}")
if spell:
    problems.append("Misspelled names: " + "; ".join(sorted(spell)[:10]))
# Arizona shows: every venue needs an address in venues.js so the show gets Directions (and tap-to-call when it has a phone)
try:
    vs = json.loads(subprocess.run(["node", "-e", "const fs=require('fs');eval(fs.readFileSync('venues.js','utf8')+fs.readFileSync('shows.js','utf8'));"
                                    "process.stdout.write(JSON.stringify([...new Set(SHOWS.map(s=>s.venue))].filter(v=>!VENUES[v]||!VENUES[v].address)))"],
                                   capture_output=True, text=True, timeout=60).stdout or "[]")
    if vs:
        problems.append("Arizona venue missing details (add address, city and phone to venues.js from the venue's own site): " + "; ".join(vs))
    else:
        notes.append("Every Arizona show's venue has an address and Directions.")
except Exception as e:
    notes.append(f"Venue check skipped ({e})")
# Radio scroll data (owner: band, song, year, country; blank when unknown). Not a problem, a to-do list:
# the Song info robot retries missing years every 30 days; the Saturday caretaker fills countries from real sources.
try:
    cat = json.load(open("show/catalog.json", encoding="utf-8"))
    bnd = json.load(open("show/bands.json", encoding="utf-8"))
    inf = json.load(open("show/songinfo.json", encoding="utf-8"))
    noc = sorted({bnd[s["b"]]["name"] for s in cat if s["b"] in bnd and not bnd[s["b"]].get("country")})
    noy = sum(1 for s in cat if not inf.get(s["v"], {}).get("y"))
    notes.append(f"Radio scroll: {noy} of {len(cat)} songs have no year yet; {len(noc)} bands have no country yet"
                 + (": " + ", ".join(noc[:15]) if noc else "") + ".")
except Exception as e:
    notes.append(f"Radio scroll check skipped ({e})")
cut = []
for f in glob.glob("*.html") + glob.glob("*/*.html"):
    m = re.search(r'name="description" content="([^"]*)"', open(f, encoding="utf-8").read())
    if m and len(m.group(1)) >= 150 and not re.search(r'[.!?…)"\']$|&quot;$', m.group(1).strip()):
        cut.append(f)
if cut:
    problems.append(f"{len(cut)} search summary(ies) cut off mid-word: " + ", ".join(cut[:8]))

# 9. Did any robot fail in the last 24 hours? (needs the gh tool, which GitHub provides)
try:
    out = subprocess.run(["gh", "run", "list", "-L", "60", "--json", "name,conclusion,createdAt,url"],
                         capture_output=True, text=True, timeout=60)
    if out.returncode == 0:
        since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24)
        fails, recovered, fixed = {}, set(), []
        for r in json.loads(out.stdout):  # newest first
            when = datetime.datetime.fromisoformat(r["createdAt"].replace("Z", "+00:00"))
            if r.get("conclusion") == "success":
                recovered.add(r["name"])  # a later run worked, so an older failure is already fixed
            if when > since and r.get("conclusion") == "failure" and r["name"] != "Site health check":
                if r["name"] in recovered:
                    if r["name"] not in fixed:
                        fixed.append(r["name"])
                else:
                    fails.setdefault(r["name"], r["url"])
        if fixed:
            notes.append("Failed earlier but ran fine since: " + ", ".join(fixed) + ".")
        if fails:
            problems.append("Robots that failed in the last 24 hours: " + "; ".join(f"{n} ({u})" for n, u in fails.items()))
        else:
            notes.append("No robot failed in the last 24 hours.")
    else:
        notes.append("Robot run list not available here.")
except FileNotFoundError:
    notes.append("Robot run list not available here (no gh).")

# 10. Brand watch (owner, Nov 26, 2026): every HeavyMusix domain stays paid and locked,
# and the site's security certificate stays valid. Expiry soon = problem; unlocked = note.
DOMAINS = ["heavymusix.com", "heavymusix.net", "heavymetalworld.com", "heavymetalworld.net",
           "heavymusicworld.com", "heavymusicworld.net"]
utcnow = datetime.datetime.now(datetime.timezone.utc)
unlocked = []
for d in DOMAINS:
    tld = d.rsplit(".", 1)[1]
    try:
        req = urllib.request.Request(f"https://rdap.verisign.com/{tld}/v1/domain/{d}",
                                     headers={"User-Agent": "HeavyMusix health check"})
        info = json.load(urllib.request.urlopen(req, timeout=30))
        exp = next((e["eventDate"] for e in info.get("events", []) if e.get("eventAction") == "expiration"), None)
        if exp:
            days = (datetime.datetime.fromisoformat(exp.replace("Z", "+00:00")) - utcnow).days
            if days < 45:
                problems.append(f"Domain {d} expires in {days} days: renew it in GoDaddy (turn Auto-renew on).")
        if "client transfer prohibited" not in info.get("status", []):
            unlocked.append(d)
    except Exception as e:
        notes.append(f"Could not check domain {d} ({e}).")
if unlocked:
    notes.append("Domains without the GoDaddy transfer lock: " + ", ".join(unlocked) + ".")
else:
    notes.append("All HeavyMusix domains are locked.")
try:
    import socket, ssl
    with socket.create_connection(("heavymusix.com", 443), timeout=30) as s:
        with ssl.create_default_context().wrap_socket(s, server_hostname="heavymusix.com") as t:
            cert_end = datetime.datetime.strptime(t.getpeercert()["notAfter"], "%b %d %H:%M:%S %Y %Z")
    cert_days = (cert_end.replace(tzinfo=datetime.timezone.utc) - utcnow).days
    if cert_days < 14:
        problems.append(f"The site's security certificate expires in {cert_days} days (GitHub Pages should renew it; check Settings > Pages).")
    else:
        notes.append(f"Security certificate good for {cert_days} more days.")
except Exception as e:
    problems.append(f"Could not check the site's security certificate ({e}).")

report = ["# HeavyMusix health check", f"Checked {now.strftime('%Y-%m-%d %H:%M')} Arizona time.", ""]
report += ["## Problems"] + [f"- {p}" for p in problems] + [""] if problems else ["All good."]
report += ["## Details"] + [f"- {n}" for n in notes]
open("health_report.md", "w").write("\n".join(report) + "\n")
print("\n".join(report))
sys.exit(1 if problems else 0)
