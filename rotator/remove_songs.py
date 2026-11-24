"""
Removes songs the owner asked to take OFF the HeavyMusix Radio playlist, and keeps them off.

rotator/remove_queue.json lists them: {"songs": [{"band", "song", "v" (video id), "status"}]}.
"pending" songs are deleted from the main playlist (every copy of that video), then marked
"removed". Removed songs stay in this file on purpose: add_songs.py and the weekly song scout
read it and never add them back. Writes how many YouTube changes it made (50 units each) to
removed_today.txt so the reshuffle budget shrinks to stay inside YouTube's daily limit.

Usage:  python remove_songs.py --apply      (without --apply it only shows what it would do)
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
QUEUE = os.path.join(HERE, "remove_queue.json")
COUNT = os.path.join(HERE, "removed_today.txt")
sys.path.insert(0, HERE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    open(COUNT, "w").write("0")
    data = json.load(open(QUEUE, encoding="utf-8")) if os.path.exists(QUEUE) else {"songs": []}
    todo = [s for s in data["songs"] if s.get("status") == "pending"]
    if not todo:
        print("No songs waiting to be removed.")
        return
    import playlist_rotator as R
    yt = R.youtube_client(scheduled=True)
    main_id = R.extract_id(open(R.LINK_FILE, encoding="utf-8-sig").read())
    in_main = {}
    for it in R.fetch_items(yt, main_id):
        v = it.get("snippet", {}).get("resourceId", {}).get("videoId")
        in_main.setdefault(v, []).append(it["id"])
    changes = 0
    for s in todo:
        try:
            items = in_main.get(s["v"], [])
            for item_id in items:
                if not a.apply:
                    print(f"   would remove: {s['band']} - {s['song']}")
                    continue
                yt.playlistItems().delete(id=item_id).execute()
                changes += 1
            if a.apply:
                s["status"] = "removed"
                print(f"   removed: {s['band']} - {s['song']}" + ("" if items else " (was already off the playlist)"))
        except Exception as e:
            msg = str(e)
            print(f"   could not remove {s['band']} - {s['song']}: {msg[:160]}")
            if "quota" in msg.lower():
                print("   YouTube's daily limit reached; the rest come off tomorrow.")
                break
    open(COUNT, "w").write(str(changes))
    if a.apply:
        json.dump(data, open(QUEUE, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    left = sum(1 for s in data["songs"] if s.get("status") == "pending")
    print(f"Removed: {changes} YouTube changes today; {left} song(s) still waiting.")


if __name__ == "__main__":
    main()
