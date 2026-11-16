"""HeavyMusix Radio Show builder.

Runs on GitHub Actions (free). Each run it:
  1. Reads the HeavyMusix Radio playlist from YouTube -> show/catalog.json
  2. Keeps the band directory up to date -> show/bands.json (never removes Heavy's edits)
  3. Plans episodes ahead (5-episode buffer) with fair rotation:
       - no band repeats until every band has played, then a new random round
       - no song by a band repeats until all of that band's songs have played
       - bands Heavy has selected as unsigned picks get guaranteed spots every episode
  4. Looks for Heavy's uploaded DJ clips (titles containing E001-01 style codes)
  5. Marks episodes ready when every clip is uploaded, and releases one a week
Writes show/episodes.json for the website. Python standard library only.
"""
import json, os, re, random, urllib.request, datetime as dt

PLAYLIST = "PLcJENP7Pnf5xXQk-R_SlBiDXeaSlSSJ6M"
CHANNEL_HANDLE = "@HeavyMusix"
SONGS_PER_EPISODE = 12
UNSIGNED_SLOTS = 3
NEWS_AFTER_SONG = 6
BUFFER = 5
RELEASE_GAP_DAYS = 7
DIR = "show"
AZ = dt.timezone(dt.timedelta(hours=-7))

# Channel names that are not the band's own name
ALIASES = {
    "Jinjer Metal Band": "Jinjer", "Jinjer Metal Band and Napalm Records": "Jinjer",
    "Dr. Otep Shamaya, Esquire": "Otep", "Cryptopsy Official": "Cryptopsy",
    "HAVOKband": "Havok", "Spiritbox Official": "Spiritbox", "Annihilator Official": "Annihilator",
    "Diamond Head Official": "Diamond Head", "OfficialIcedEarth": "Iced Earth",
    "Body Count Band Official": "Body Count", "ANALEPSY Official": "Analepsy",
    "TheHauntedOfficial": "The Haunted", "Rings of Saturn Band Official": "Rings of Saturn",
    "Archspiremetal": "Archspire", "TERRIFIER - CANADA": "Terrifier", "WatchTower": "Watchtower",
    "BeyondCreation": "Beyond Creation", "destrage": "Destrage", "DECAPITATED": "Decapitated",
    "POWER TRIP": "Power Trip", "MELVINS": "Melvins", "BATTLECROSS": "Battlecross",
    "GOROD": "Gorod", "DOWN": "Down", "BAEST": "Baest", "SpiritWorldProphet": "SpiritWorld",
}
# Uploader channels (labels, fan channels): take the band from the video title instead
UPLOADERS = {"Napalm Records", "Prosthetic Records", "MetalSinPantalones", "AGNT Thrasher",
             "Ola Englund", "Nuclear Blast Records", "Century Media Records", "Metal Blade Records"}
TITLE_FIX = {"EVILE": "Evile", "FEARED": "Feared", "Havok": "Havok", "Psycroptic": "Psycroptic", "Aggression": "Aggression"}


def slug(s):
    s = s.lower().replace("&", "and")
    s = re.sub(r"[^\w]+", "-", s, flags=re.UNICODE).strip("-")
    return s or "band"


def clean_song(title, band):
    t = re.sub(r"\s*\|.*$", "", title)
    t = re.sub(r"\s*[\(\[](official|hd|lyric|music video|audio|visualizer)[^\)\]]*[\)\]]", "", t, flags=re.I)
    if band and t.lower().startswith(band.lower() + " - "):
        t = t[len(band) + 3:]
    return t.strip() or title


def band_for(title, channel):
    ch = re.sub(r" - Topic$", "", channel).strip()
    if ch in UPLOADERS:
        m = re.match(r"\s*([^\-\"“]+?)\s*(?:-|\"|“)", title)
        if m:
            name = m.group(1).strip()
            return TITLE_FIX.get(name, name.title() if name.isupper() else name)
        return ch
    return ALIASES.get(ch, ch)


# ---------- YouTube reading (public pages, no sign-in) ----------
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9", "Cookie": "CONSENT=YES+1; SOCS=CAI"}


def http(url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    h = dict(UA)
    if data:
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=h)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def _item(o):
    if not isinstance(o, dict):
        return None
    if "lockupViewModel" in o:
        x = o["lockupViewModel"]
        if x.get("contentType") != "LOCKUP_CONTENT_TYPE_VIDEO":
            return None
        md = (x.get("metadata") or {}).get("lockupMetadataViewModel") or {}
        try:
            ch = md["metadata"]["contentMetadataViewModel"]["metadataRows"][0]["metadataParts"][0]["text"]["content"]
        except Exception:
            ch = ""
        return {"v": x.get("contentId"), "t": (md.get("title") or {}).get("content", ""), "c": ch}
    if "playlistVideoRenderer" in o:
        r = o["playlistVideoRenderer"]
        return {"v": r.get("videoId"), "t": ((r.get("title") or {}).get("runs") or [{}])[0].get("text", ""),
                "c": ((r.get("shortBylineText") or {}).get("runs") or [{}])[0].get("text", "")}
    return None


def _walk(o, out):
    it = _item(o)
    if it:
        out.append(it)
        return
    if isinstance(o, dict):
        for v in o.values():
            _walk(v, out)
    elif isinstance(o, list):
        for v in o:
            _walk(v, out)


def read_playlist(pl):
    html = http(f"https://www.youtube.com/playlist?list={pl}&hl=en")
    ver = re.search(r'"INNERTUBE_CLIENT_VERSION":"([^"]+)', html).group(1)
    raw = re.search(r"var ytInitialData = (\{.*?\});</script>", html, re.S).group(1)
    out = []
    _walk(json.loads(raw), out)
    m = re.search(r'"continuationCommand":\{"token":"([^"]+)"', raw)
    tok, pages = (m.group(1) if m else None), 0
    while tok and pages < 60:
        pages += 1
        j = json.loads(http("https://www.youtube.com/youtubei/v1/browse?prettyPrint=false",
                            {"context": {"client": {"clientName": "WEB", "clientVersion": ver, "hl": "en", "gl": "US"}},
                             "continuation": tok}))
        arr = []
        for a in j.get("onResponseReceivedActions", []):
            arr += (a.get("appendContinuationItemsAction") or {}).get("continuationItems", [])
        n, tok = 0, None
        for o in arr:
            it = _item(o)
            if it:
                out.append(it)
                n += 1
            else:
                mm = re.search(r'"token":"([^"]+)"', json.dumps(o, separators=(",", ":")))
                if mm:
                    tok = mm.group(1)
        if not n:
            break
    seen, uniq = set(), []
    for x in out:
        if x["v"] and x["v"] not in seen:
            seen.add(x["v"])
            uniq.append(x)
    return uniq


def channel_uploads():
    html = http(f"https://www.youtube.com/{CHANNEL_HANDLE}?hl=en")
    m = re.search(r'"(?:externalId|channelId)":"(UC[\w-]{22})"', html)
    if not m:
        return []
    return read_playlist("UU" + m.group(1)[2:])


# ---------- files ----------
def load(name, default):
    p = os.path.join(DIR, name)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return default


def save(name, data):
    os.makedirs(DIR, exist_ok=True)
    with open(os.path.join(DIR, name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")


# ---------- planning ----------
def clip_code(ep, k):
    return f"E{ep:03d}-{k:02d}"


def plan_episode(n, catalog, bands, state, rng):
    # Skip songs that can't play on the site (found weekly by scripts/check_songs.py)
    bad = {x["v"] for x in load("unplayable.json", {"songs": []}).get("songs", [])}
    by_band = {}
    for s in catalog:
        if s["v"] not in bad:
            by_band.setdefault(s["b"], []).append(s["v"])
    unsigned = sorted(b for b in by_band if bands.get(b, {}).get("unsigned"))
    picks = []

    def next_song(b):
        cyc = [v for v in state["songs"].get(b, []) if v in by_band[b]]
        if not cyc:
            cyc = by_band[b][:]
            rng.shuffle(cyc)
        v = cyc.pop(0)
        state["songs"][b] = cyc
        return v

    # Guaranteed unsigned spots, rotating fairly among Heavy's picks
    for _ in range(min(UNSIGNED_SLOTS, len(unsigned))):
        q = [b for b in state.get("unsigned_cycle", []) if b in unsigned and b not in picks]
        if not q:
            q = [b for b in unsigned if b not in picks]
            rng.shuffle(q)
        b = q.pop(0)
        state["unsigned_cycle"] = q
        picks.append(b)

    # Main rotation: every band once before anyone repeats (unsigned picks have their own spots)
    pool = [b for b in by_band if b not in unsigned] or list(by_band)
    target = min(SONGS_PER_EPISODE, len(picks) + len(pool))
    guard = 0
    while len(picks) < target and guard < 5000:
        guard += 1
        cyc = [b for b in state.get("band_cycle", []) if b in pool]
        if not cyc:
            cyc = pool[:]
            rng.shuffle(cyc)
            if cyc[0] == state.get("last_band") and len(cyc) > 1:
                cyc.append(cyc.pop(0))
        b = cyc.pop(0)
        state["band_cycle"] = cyc
        if b in picks:
            continue
        picks.append(b)
        state["last_band"] = b

    # Spread unsigned picks through the hour instead of bunching them at the start
    unsigned_picks = [b for b in picks if b in unsigned][:UNSIGNED_SLOTS]
    rest = [b for b in picks if b not in unsigned_picks]
    order = rest[:]
    for i, b in enumerate(unsigned_picks):
        pos = min(len(order), 2 + i * 4)
        order.insert(pos, b)

    songs = []
    title_of = {s["v"]: s for s in catalog}
    for b in order:
        v = next_song(b)
        s = title_of[v]
        songs.append({"v": v, "b": b, "band": bands.get(b, {}).get("name", s["n"]), "song": s["t"]})

    clips = [{"code": clip_code(n, 1), "role": "Show open"}]
    seq = [{"clip": clip_code(n, 1)}]
    k = 2
    for i, s in enumerate(songs, 1):
        if i == NEWS_AFTER_SONG + 1:
            clips.append({"code": clip_code(n, 90), "role": "News break"})
            seq.append({"clip": clip_code(n, 90)})
        role = ("Unsigned spotlight: " if bands.get(s["b"], {}).get("unsigned") else "Intro: ") + s["band"] + " - " + s["song"]
        clips.append({"code": clip_code(n, k), "role": role})
        seq.append({"clip": clip_code(n, k)})
        seq.append({"song": s["v"]})
        k += 1
    clips.append({"code": clip_code(n, 99), "role": "Show close"})
    seq.append({"clip": clip_code(n, 99)})
    return {"n": n, "title": f"HeavyMusix Radio Show #{n}", "songs": songs, "clips": clips, "seq": seq,
            "status": "needs_voice", "planned": dt.datetime.now(AZ).strftime("%Y-%m-%d")}


def main():
    rng = random.Random()
    today = dt.datetime.now(AZ).date()

    # 1. Catalog
    old = load("catalog.json", [])
    try:
        raw = read_playlist(PLAYLIST)
        print(f"Playlist read: {len(raw)} videos")
    except Exception as e:
        print(f"Could not read playlist ({e}); keeping the saved catalog")
        raw = None
    if raw:
        catalog = []
        for x in raw:
            name = band_for(x["t"], x["c"])
            catalog.append({"v": x["v"], "t": clean_song(x["t"], name), "n": name, "b": slug(name)})
        save("catalog.json", catalog)
    else:
        catalog = old
    if not catalog:
        print("No catalog yet; nothing to plan")
        return

    # 2. Band directory (keep everything Heavy or Claude already filled in)
    bands = load("bands.json", {})
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("bandinfo", os.path.join("scripts", "bandinfo.py"))
        info = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(info)
        known = info.B
    except Exception:
        known = {}
    counts = {}
    for s in catalog:
        counts[s["b"]] = counts.get(s["b"], 0) + 1
        if s["b"] not in bands:
            city, region, country, genre = known.get(s["n"], ("", "", "", ""))
            bands[s["b"]] = {"name": s["n"], "city": city, "region": region, "country": country,
                             "genre": genre, "unsigned": False, "links": {}, "bio": ""}
        else:
            kn = known.get(bands[s["b"]].get("name", s["n"]))
            if kn:
                for f, val in zip(("city", "region", "country", "genre"), kn):
                    if not bands[s["b"]].get(f):
                        bands[s["b"]][f] = val
    for b in bands:
        bands[b]["songs"] = counts.get(b, 0)
    save("bands.json", bands)

    # 3. Plan episodes to keep the buffer full
    state = load("state.json", {"band_cycle": [], "songs": {}, "unsigned_cycle": [], "episodes": []})
    eps = state["episodes"]
    waiting = [e for e in eps if e["status"] != "live"]
    while len(waiting) < BUFFER:
        n = (eps[-1]["n"] + 1) if eps else 1
        e = plan_episode(n, catalog, bands, state, rng)
        eps.append(e)
        waiting.append(e)
        print(f"Planned episode {n}")

    # 4. Find Heavy's uploaded DJ clips
    try:
        uploads = channel_uploads()
    except Exception as e:
        print(f"Could not read channel uploads ({e})")
        uploads = []
    found = {}
    for u in uploads:
        m = re.search(r"E(\d{3})-(\d{2})", u["t"])
        if m:
            found[f"E{m.group(1)}-{m.group(2)}"] = u["v"]
    print(f"DJ clips found: {len(found)}")

    # 5. Ready / release (one episode a week; first one the day it is ready)
    last_live = max((dt.date.fromisoformat(e["live"]) for e in eps if e.get("live")), default=None)
    for e in eps:
        for c in e["clips"]:
            if c["code"] in found:
                c["v"] = found[c["code"]]
        have = sum(1 for c in e["clips"] if c.get("v"))
        e["clips_done"], e["clips_total"] = have, len(e["clips"])
        if e["status"] == "live":
            continue
        if have == len(e["clips"]):
            e["status"] = "ready"
            due = today if last_live is None else last_live + dt.timedelta(days=RELEASE_GAP_DAYS)
            prev = [x for x in eps if x["n"] < e["n"]]
            if all(x["status"] == "live" for x in prev) and today >= due:
                e["status"] = "live"
                e["live"] = today.isoformat()
                last_live = today
                print(f"Episode {e['n']} is now LIVE")
        else:
            e["status"] = "needs_voice"
    save("state.json", state)

    # Public file for the website and the script writer
    pub = []
    for e in eps:
        item = {"n": e["n"], "title": e["title"], "status": e["status"], "live": e.get("live"),
                "clips_done": e["clips_done"], "clips_total": e["clips_total"],
                "songs": e["songs"], "clips": [{"code": c["code"], "role": c["role"]} for c in e["clips"]]}
        if e["status"] == "live":
            vmap = {c["code"]: c.get("v") for c in e["clips"]}
            item["play"] = [vmap[s["clip"]] if "clip" in s else s["song"] for s in e["seq"]]
        pub.append(item)
    ready_ahead = sum(1 for e in eps if e["status"] == "ready")
    save("episodes.json", {"updated": dt.datetime.now(AZ).isoformat(timespec="minutes"),
                           "playlist": PLAYLIST, "ready_ahead": ready_ahead, "episodes": pub})
    print(f"Done. Live: {sum(1 for e in eps if e['status']=='live')}, ready ahead: {ready_ahead}")


if __name__ == "__main__":
    main()
