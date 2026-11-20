"""Song info robot: finds the album and year for every song on HeavyMusix Radio.

Reads show/catalog.json (song title "t", band name "n", YouTube id "v") and
looks each song up on MusicBrainz (free, open music database). Writes
show/songinfo.json: {"<youtube id>": {"al": "<album>", "y": 1986}}.
The radio player shows it in the scrolling "now playing" line.

Only songs not looked up yet (or not found, retried after 30 days) are
searched, so daily runs are quick. MusicBrainz asks for at most one request
per second and a User-Agent that says who we are.
"""
import datetime as dt
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request

CATALOG = "show/catalog.json"
OUT = "show/songinfo.json"
UA = "HeavyMusix/1.0 ( info@heavymusix.com )"
MAX_LOOKUPS = 750
RETRY_DAYS = 30


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\(.*?\)|\[.*?\]", " ", s)
    s = re.sub(r"\b(the|official|video|audio|lyric|lyrics|remaster(ed)?|live)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def q(s):
    return '"' + (s or "").replace("\\", " ").replace('"', " ") + '"'


def search(title, band):
    query = f"recording:{q(title)} AND artist:{q(band)}"
    url = "https://musicbrainz.org/ws/2/recording?" + urllib.parse.urlencode({"query": query, "fmt": "json", "limit": 25})
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r).get("recordings", [])


def year_of(d):
    m = re.match(r"(\d{4})", d or "")
    return int(m.group(1)) if m else None


def pick(recs, title, band):
    """Best album for this song: the earliest official studio album it appeared on."""
    nt, nb = norm(title), norm(band)
    best = None
    for rec in recs:
        if norm(rec.get("title")) != nt:
            continue
        artists = "".join(norm(a.get("name") or a.get("artist", {}).get("name")) for a in rec.get("artist-credit", []))
        if nb not in artists and artists not in nb:
            continue
        for rel in rec.get("releases", []):
            rg = rel.get("release-group", {})
            if rel.get("status", "Official") != "Official":
                continue
            ptype = rg.get("primary-type") or ""
            secondary = rg.get("secondary-types") or []
            if "Compilation" in secondary or "Live" in secondary:
                rank = 3
            elif ptype == "Album":
                rank = 0
            elif ptype == "EP":
                rank = 1
            else:
                rank = 2
            y = year_of(rel.get("date")) or year_of(rec.get("first-release-date"))
            key = (rank, y or 9999)
            if best is None or key < best[0]:
                best = (key, rg.get("title") or rel.get("title"), y)
    if not best:
        return None
    return {"al": best[1], "y": best[2]} if best[2] else {"al": best[1]}


def main():
    catalog = json.load(open(CATALOG, encoding="utf-8"))
    try:
        info = json.load(open(OUT, encoding="utf-8"))
    except (OSError, ValueError):
        info = {}
    today = dt.date.today()
    todo = []
    for s in catalog:
        v = s.get("v")
        if not v or not s.get("t") or not s.get("n"):
            continue
        have = info.get(v)
        if have and have.get("al"):
            continue
        if have and have.get("miss"):
            try:
                if (today - dt.date.fromisoformat(have["miss"])).days < RETRY_DAYS:
                    continue
            except ValueError:
                pass
        todo.append(s)
    print(f"{len(catalog)} songs, {len(todo)} to look up")
    found = 0
    for s in todo[:MAX_LOOKUPS]:
        try:
            got = pick(search(s["t"], s["n"]), s["t"], s["n"])
        except Exception as e:
            print(f"  lookup failed for {s['n']} - {s['t']}: {e}")
            time.sleep(3)
            continue
        if got:
            info[s["v"]] = got
            found += 1
        else:
            info[s["v"]] = {"miss": today.isoformat()}
        time.sleep(1.1)
    keep = {s["v"] for s in catalog}
    info = {k: v for k, v in info.items() if k in keep}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=0, sort_keys=True)
        f.write("\n")
    total = sum(1 for v in info.values() if v.get("al"))
    print(f"Found {found} new; {total} of {len(catalog)} songs have album info")


if __name__ == "__main__":
    main()
