"""
Moves "roots" songs (classical and jazz, saved for a future Radio Show idea) out of the main
HeavyMusix Radio playlist into a separate PRIVATE playlist, "HeavyMusix Roots".

Runs inside the daily Playlist reshuffle workflow, before the reshuffle. It only does work when
rotator/roots_pending.json lists songs still to move; otherwise it costs nothing.

Safe order for each song: add it to Roots first, confirm, then remove it from the main playlist.
Nothing else is ever removed. Writes how many YouTube units it spent (in songs moved) to
roots_moved_today.txt so the reshuffle budget can shrink to stay inside YouTube's daily limit.

Usage:  python roots_move.py --apply      (without --apply it only shows what it would do)
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PENDING = os.path.join(HERE, "roots_pending.json")
ROOTS_FILE = os.path.join(HERE, "roots_playlist.txt")
COUNT = os.path.join(HERE, "roots_moved_today.txt")
TITLE = "HeavyMusix Roots"
DESC = "Classical and jazz picks saved for a future HeavyMusix Radio Show idea."
sys.path.insert(0, HERE)


def roots_id(yt, apply):
    if os.path.exists(ROOTS_FILE):
        pid = open(ROOTS_FILE, encoding="utf-8").read().strip()
        if pid:
            return pid
    token = None
    while True:   # reuse one that already exists with this title
        r = yt.playlists().list(part="snippet", mine=True, maxResults=50, pageToken=token).execute()
        for p in r.get("items", []):
            if p["snippet"]["title"] == TITLE:
                open(ROOTS_FILE, "w", encoding="utf-8").write(p["id"] + "\n")
                return p["id"]
        token = r.get("nextPageToken")
        if not token:
            break
    if not apply:
        print(f"   would create the private playlist \"{TITLE}\"")
        return None
    p = yt.playlists().insert(part="snippet,status", body={
        "snippet": {"title": TITLE, "description": DESC},
        "status": {"privacyStatus": "private"}}).execute()
    open(ROOTS_FILE, "w", encoding="utf-8").write(p["id"] + "\n")
    print(f"   created private playlist \"{TITLE}\": https://www.youtube.com/playlist?list={p['id']}")
    return p["id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    open(COUNT, "w").write("0")
    data = json.load(open(PENDING, encoding="utf-8")) if os.path.exists(PENDING) else {"songs": []}
    todo = [s for s in data["songs"] if s.get("status") != "moved"]
    if not todo:
        print("No roots songs waiting to move.")
        return
    import playlist_rotator as R
    yt = R.youtube_client(scheduled=True)
    main_id = R.extract_id(open(R.LINK_FILE, encoding="utf-8-sig").read())
    rid = roots_id(yt, a.apply)
    if rid == main_id:
        sys.exit("Refusing: the Roots playlist id is the main playlist id.")
    in_main = {}
    for it in R.fetch_items(yt, main_id):
        v = it.get("snippet", {}).get("resourceId", {}).get("videoId")
        in_main.setdefault(v, []).append(it["id"])
    in_roots = set()
    if rid:
        for it in R.fetch_items(yt, rid):
            in_roots.add(it.get("snippet", {}).get("resourceId", {}).get("videoId"))
    moved = 0
    for s in todo:
        v = s["v"]
        try:
            if v not in in_roots:
                if not a.apply:
                    print(f"   would add to Roots: {s['band']} - {s['song']}")
                else:
                    yt.playlistItems().insert(part="snippet", body={"snippet": {
                        "playlistId": rid, "resourceId": {"kind": "youtube#video", "videoId": v}}}).execute()
                    in_roots.add(v)
                    moved += 1
            for item_id in in_main.get(v, []):
                if not a.apply:
                    print(f"   would remove from main: {s['band']} - {s['song']}")
                    continue
                if v not in in_roots:
                    raise RuntimeError("not confirmed in Roots; leaving it in the main playlist")
                yt.playlistItems().delete(id=item_id).execute()
                moved += 1
            if a.apply:
                s["status"] = "moved"
                print(f"   moved to Roots: {s['band']} - {s['song']}")
        except Exception as e:
            msg = str(e)
            print(f"   could not move {s['band']} - {s['song']}: {msg[:160]}")
            if "quota" in msg.lower():
                print("   YouTube's daily limit reached; the rest move tomorrow.")
                break
    open(COUNT, "w").write(str(moved))
    if a.apply:
        json.dump(data, open(PENDING, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    left = sum(1 for s in data["songs"] if s.get("status") != "moved")
    print(f"Roots: {moved} YouTube changes today; {left} song(s) still to move.")


if __name__ == "__main__":
    main()
