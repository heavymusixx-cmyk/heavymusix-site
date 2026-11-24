"""
Adds songs from add_queue.json to the HeavyMusix Radio playlist, a few a day.

Why a few a day: YouTube gives the playlist robot about 10,000 "units" a day. The morning
reshuffle uses about 9,000 (each moved song costs 50). Adding a song also costs 50, so this
adds up to --max songs (default 20 = 1,000 units) and writes how many it added to
added_today.txt; the workflow then gives the reshuffle that much less budget.

Finding the right video: YouTube Music search (ytmusicapi, which costs no YouTube units).
A result is used only if its title and artist both match the queued song; otherwise the
song is marked not_found for a person to add by hand. Nothing is ever removed.

Usage:  python add_songs.py --apply [--max 20]     (without --apply it only shows what it would do)
"""
import argparse, json, os, re, sys, time, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
QUEUE = os.path.join(HERE, "add_queue.json")
COUNT = os.path.join(HERE, "added_today.txt")
sys.path.insert(0, HERE)


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\((?:[^)]*(?:remaster|live|official|video|audio|lyric|version|edit|explicit|feat|ft\.)[^)]*)\)|\[[^\]]*\]", "", s)
    s = re.sub(r"\b(feat|ft)\.?\s.*$", "", s)
    return re.sub(r"[^a-z0-9]", "", s.replace("&", "and"))


def owner_blocks():
    """Songs and bands the owner removed (remove_queue.json): (video ids, (band, song) pairs, bands), all normalized."""
    try:
        d = json.load(open(os.path.join(HERE, "remove_queue.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return set(), set(), set()
    songs = d.get("songs", [])
    return ({s.get("v") for s in songs if s.get("v")},
            {(norm(s["band"]), norm(s["song"])) for s in songs},
            {norm(b["band"]) for b in d.get("blocked_bands", [])})


def first_band(band):
    return re.split(r",| vs\.? | & | and ", band, maxsplit=1)[0].strip()


def good_match(want_band, want_song, title, artists):
    """True when the result's title is the song and one of its artists is the (first) band."""
    t, s = norm(title), norm(want_song)
    if not s or not (t == s or (t.startswith(s) and len(t) - len(s) <= 6)):
        return False
    b = norm(first_band(want_band))
    return any(b and (b == norm(a) or b in norm(a) or norm(a) in b) for a in artists if norm(a))


def find_video(search, band, song):
    """search(query) -> list of {videoId, title, artists:[names]}.
    Returns (videoId or None, whether the search returned anything at all)."""
    got_any = False
    for q in (f"{band} {song}", f"{first_band(band)} {song}"):
        res = search(q)
        got_any = got_any or bool(res)
        for r in res[:8]:
            if r.get("videoId") and good_match(band, song, r.get("title", ""), r.get("artists", [])):
                return r["videoId"], True
    return None, got_any


def ytmusic_search():
    from ytmusicapi import YTMusic
    ym = YTMusic()
    def search(q):
        out = []
        for flt in ("songs", "videos"):
            try:
                for r in ym.search(q, filter=flt, limit=8):
                    out.append({"videoId": r.get("videoId"), "title": r.get("title", ""),
                                "artists": [a.get("name", "") for a in (r.get("artists") or [])]})
            except Exception as e:
                print(f"   search problem ({flt}): {e}")
            time.sleep(0.5)
        return out
    return search


def roots_bands():
    """Normalized names of classical/jazz acts (scripts/bandinfo.py genre), kept off the main playlist."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("bandinfo", os.path.join(HERE, "..", "scripts", "bandinfo.py"))
        info = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(info)
        return {norm(n) for n, v in info.B.items() if len(v) > 3 and v[3] in ("Classical", "Jazz")}
    except Exception:
        return set()


def run(yt, playlist_id, search, queue, max_add, apply, fetch_items):
    """Adds up to max_add queued songs. Returns how many were added. Updates queue in place."""
    have_vids, have_titles = set(), set()
    for it in fetch_items(yt, playlist_id):
        sn = it.get("snippet", {})
        have_vids.add(sn.get("resourceId", {}).get("videoId"))
        have_titles.add(norm(sn.get("title", "")))
    added, blank = 0, 0
    roots = roots_bands()
    blocked_vids, blocked_songs, blocked_bands = owner_blocks()
    for q in queue:
        if added >= max_add:
            break
        if q.get("status") not in ("queued", "failed"):
            continue
        if (q.get("videoId") in blocked_vids or (norm(first_band(q["band"])), norm(q["song"])) in blocked_songs
                or norm(first_band(q["band"])) in blocked_bands):   # the owner took these off: never add back
            q["status"] = "blocked"
            print(f"   blocked by the owner, not added: {q['band']} - {q['song']}")
            continue
        if norm(first_band(q["band"])) in roots:   # classical/jazz never go in the main playlist
            q["status"] = "held_roots"
            print(f"   held for the Roots playlist (not added): {q['band']} - {q['song']}")
            continue
        vid, got_any = find_video(search, q["band"], q["song"])
        if not got_any:
            blank += 1
            if blank >= 3:
                print("   YouTube Music search is returning nothing; leaving the rest queued for tomorrow.")
                break
            continue
        blank = 0
        if not vid:
            q["status"] = "not_found"
            print(f"   not found (add by hand if you want it): {q['band']} - {q['song']}")
            continue
        if vid in have_vids:
            q["status"], q["videoId"] = "already_there", vid
            continue
        if not apply:
            print(f"   would add: {q['band']} - {q['song']} ({vid})")
            added += 1
            continue
        try:
            yt.playlistItems().insert(part="snippet", body={"snippet": {
                "playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute()
            q["status"], q["videoId"] = "added", vid
            have_vids.add(vid)
            added += 1
            print(f"   added: {q['band']} - {q['song']}")
        except Exception as e:
            msg = str(e)
            q["status"] = "failed"
            print(f"   could not add {q['band']} - {q['song']}: {msg[:160]}")
            if "quota" in msg.lower():
                print("   YouTube's daily limit reached; the rest wait for tomorrow.")
                break
    return added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--max", type=int, default=20)
    a = ap.parse_args()
    data = json.load(open(QUEUE, encoding="utf-8"))
    left = [q for q in data["songs"] if q.get("status") in ("queued", "failed")]
    open(COUNT, "w").write("0")
    if not left:
        print("Nothing waiting to be added.")
        return
    import playlist_rotator as R
    yt = R.youtube_client(scheduled=True)
    pid = R.extract_id(open(R.LINK_FILE).read())
    n = run(yt, pid, ytmusic_search(), data["songs"], a.max, a.apply, R.fetch_items)
    open(COUNT, "w").write(str(n if a.apply else 0))
    json.dump(data, open(QUEUE, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    s = {}
    for q in data["songs"]:
        s[q["status"]] = s.get(q["status"], 0) + 1
    print(f"Added today: {n}. Queue now: " + ", ".join(f"{v} {k}" for k, v in sorted(s.items())))


if __name__ == "__main__":
    main()
