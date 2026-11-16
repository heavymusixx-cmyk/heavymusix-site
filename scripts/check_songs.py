"""HeavyMusix song check: finds playlist songs that cannot play inside heavymusix.com.

YouTube lets each uploader turn off playing their video on other websites, and videos
get removed or made private. This asks YouTube's public oEmbed address about every
song in show/catalog.json and writes show/unplayable.json:
  401/403 = the owner turned off playing it on other sites (it still plays on YouTube)
  404/400 = removed, private or broken
The player, band pages and the Radio Show planner skip these songs, and the owner gets
a list to replace in the playlist. Python standard library only. Runs on GitHub Actions.
"""
import json, time, urllib.request, urllib.error, datetime as dt

REASON = {401: "embedding off", 403: "embedding off", 404: "removed or private", 400: "removed or private"}


def status(v):
    url = "https://www.youtube.com/oembed?format=json&url=https%3A//www.youtube.com/watch%3Fv%3D" + v
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (HeavyMusix song check; +https://heavymusix.com)"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status
        except urllib.error.HTTPError as e:
            if e.code in REASON:
                return e.code
            if e.code == 429:
                time.sleep(10 * (attempt + 1))
                continue
            return None   # other errors: unknown, do not mark the song
        except Exception:
            time.sleep(2)
    return None


def main():
    catalog = json.load(open("show/catalog.json", encoding="utf-8"))
    bad, unknown = [], 0
    for i, s in enumerate(catalog):
        code = status(s["v"])
        if code is None:
            unknown += 1
        elif code in REASON:
            bad.append({"v": s["v"], "band": s["n"], "song": s["t"], "why": REASON[code]})
            print(f"{s['n']} - {s['t']}: {REASON[code]}")
        time.sleep(0.25)
    if unknown > len(catalog) // 2:
        print(f"Could not check {unknown} songs; keeping the old list")
        return
    out = {"updated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"),
           "checked": len(catalog), "songs": bad}
    with open("show/unplayable.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"Checked {len(catalog)} songs: {len(bad)} cannot play on the site, {unknown} could not be checked")


if __name__ == "__main__":
    main()
