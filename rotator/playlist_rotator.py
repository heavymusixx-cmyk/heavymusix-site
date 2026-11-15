#!/usr/bin/env python3
"""
Playlist Rotator for YouTube Music  -  version 2 (fresh shuffle every run)

Every run deals a brand-new random order onto the TOP of your playlist:
  * every artist plays once before any artist plays again (rounds)
  * an artist's songs don't repeat until all of that artist's songs have had a turn
  * the same artist never plays twice in a row
  * NEW songs go first: a new song is its artist's pick in the earliest round,
    and artists with new songs lead that round.

YouTube allows about 200 moves a day, so each run re-deals the top 180 songs
(roughly 12 hours of music). Start listening from the top of the playlist.

Usage:
  python playlist_rotator.py            preview only, changes nothing
  python playlist_rotator.py --apply    really reorder on YouTube

Options:
  --budget N   max moves per run (default 180)
  --reset      forget which songs are new and which have had a turn
"""
import argparse, datetime, json, os, random, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
MEMORY = os.path.join(HERE, "rotator_memory.json")       # which songs are new / have had a turn
OVERRIDES = os.path.join(HERE, "artists.json")           # {"videoId": "Artist"} fixes
SECRETS = os.path.join(HERE, "client_secret.json")       # from Google Cloud
TOKEN = os.path.join(HERE, "token.json")                 # created at first sign-in
LINK_FILE = os.path.join(HERE, "playlist.txt")           # your playlist link
LOG_FILE = os.path.join(HERE, "rotator_log.txt")         # what happened on each run
SCOPES = ["https://www.googleapis.com/auth/youtube"]

NOISE = re.compile(r"\s*[\(\[][^\)\]]*(official|video|lyric|audio|visuali[sz]er|\bhd\b|4k)[^\)\]]*[\)\]]", re.I)
FEAT = re.compile(r"\s+(feat\.?|ft\.?|featuring)\s.*$", re.I)
GONE = ("Deleted video", "Private video")


# ---------------------------------------------------------------- artist logic
def clean_artist(name):
    name = FEAT.sub("", name.strip())
    name = re.sub(r"\s*-\s*Topic$", "", name, flags=re.I)
    name = re.sub(r"\s*VEVO$", "", name, flags=re.I)
    return name.strip()


def guess_artist(title, channel, override=None):
    """Returns (artist, certain). Order: your fix > Topic channel > 'Artist - Song' title > channel."""
    if override:
        return override, True
    if channel and re.search(r"-\s*Topic$", channel, re.I):
        return clean_artist(channel), True
    m = re.search(r"\s[-–—]\s", title or "")
    if m and m.start() > 0:
        return clean_artist(title[:m.start()]), True
    if channel:
        return clean_artist(channel), False
    return "Unknown", False


class Song:
    def __init__(self, item_id, video_id, title, channel, override=None, playable=True):
        self.id = item_id
        self.video_id = video_id
        self.playable = playable
        self.title = NOISE.sub("", title or "").strip() or (title or "")
        self.artist, self.certain = guess_artist(title, channel, override)
        self.key = self.artist.lower()


# ------------------------------------------------------------ ordering logic
def shuffled(xs):
    xs = list(xs)
    random.shuffle(xs)
    return xs


def build_order(songs, is_new, had_turn):
    """A fresh random order of every playable song that follows the rules.
    Each artist's line-up: new songs first, then songs that haven't had a turn, then the rest."""
    groups = {}
    for s in songs:
        groups.setdefault(s.key, []).append(s)
    queues = {}
    for k, g in groups.items():
        new = shuffled([s for s in g if is_new(s)])
        fresh = shuffled([s for s in g if not is_new(s) and s.id not in had_turn])
        used = shuffled([s for s in g if not is_new(s) and s.id in had_turn])
        queues[k] = new + fresh + used
    out, prev = [], None
    while any(queues.values()):
        ks = [k for k, q in queues.items() if q]
        lead = shuffled([k for k in ks if is_new(queues[k][0])])     # artists with a new song go first
        rest = shuffled([k for k in ks if not is_new(queues[k][0])])
        order = lead + rest
        if len(order) > 1 and order[0] == prev:                     # no artist twice in a row
            order[0], order[1] = order[1], order[0]
        for k in order:
            out.append(queues[k].pop(0))
        prev = order[-1]
    return out


def check(order):
    """Returns a list of problems in this stretch of songs (empty means the rules hold)."""
    left = {}
    for s in order:
        left[s.key] = left.get(s.key, 0) + 1
    seen = set()
    for i, s in enumerate(order):
        others = [k for k, c in left.items() if c > 0 and k != s.key]
        if s.key in seen:
            waiting = [k for k in others if k not in seen]
            if waiting:
                return [f"{s.artist} came back before {len(waiting)} other artist(s) had a turn"]
            seen = set()
        if i and order[i - 1].key == s.key and others:
            return [f"{s.artist} plays twice in a row"]
        seen.add(s.key)
        left[s.key] -= 1
    return []


# ---------------------------------------------------------------- YouTube I/O
def youtube_client(scheduled=False):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    creds = None
    if os.path.exists(TOKEN):
        creds = Credentials.from_authorized_user_file(TOKEN, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        if not creds or not creds.valid:
            if scheduled:
                print("Google sign-in is needed, but this is the automatic run so nobody can click.\n"
                      "Double-click Start-Setup.bat once to sign in again. Tip: in Google Cloud, the\n"
                      "OAuth consent screen must say 'In production' (Publish App) or sign-in expires every 7 days.")
                sys.exit(1)
            flow =InstalledAppFlow.from_client_secrets_file(SECRETS, SCOPES)
            creds = flow.run_local_server(port=0, prompt="select_account consent")
        with open(TOKEN, "w") as f:
            f.write(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def owner_check(yt, playlist_id):
    """Returns (signed-in channel name, playlist owner name, same?)."""
    me = yt.channels().list(part="snippet", mine=True).execute().get("items", [])
    pl = yt.playlists().list(part="snippet", id=playlist_id).execute().get("items", [])
    my_id = me[0]["id"] if me else None
    my_name = me[0]["snippet"]["title"] if me else "(no YouTube channel)"
    if not pl:
        return my_name, "(playlist not found - check the link in playlist.txt)", False
    return my_name, pl[0]["snippet"].get("channelTitle", "?"), pl[0]["snippet"].get("channelId") == my_id


def fetch_items(yt, playlist_id):
    items, token = [], None
    while True:
        r = yt.playlistItems().list(part="snippet", playlistId=playlist_id,
                                    maxResults=50, pageToken=token).execute()
        items += r["items"]
        token = r.get("nextPageToken")
        if not token:
            return items


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def to_songs(raw_items):
    """All items in playlist order. Deleted/private ones are kept (they still take up a spot)."""
    over = load_json(OVERRIDES, {})
    songs, raw_by_id = [], {}
    for it in raw_items:
        sn = it["snippet"]
        vid = sn.get("resourceId", {}).get("videoId", "")
        playable = sn.get("title") not in GONE
        songs.append(Song(it["id"], vid, sn.get("title", ""), sn.get("videoOwnerChannelTitle", ""),
                          over.get(vid), playable))
        raw_by_id[it["id"]] = it
    return songs, raw_by_id


def apply_moves(yt, playlist_id, current, target, raw_by_id, budget, apply):
    """Moves songs one at a time, from the top down, until the budget is used.
    Returns (moves made, how many top spots now match the plan, stop reason)."""
    cur = [s.id for s in current]
    moves = done = 0
    for pos, s in enumerate(target):
        if not s.playable:          # deleted/private videos are left at the bottom, never moved
            return moves, done, None
        if cur[pos] != s.id:
            if moves >= budget:
                return moves, done, "budget"
            if apply:
                sn = raw_by_id[s.id]["snippet"]
                try:
                    for attempt in range(6):             # YouTube sometimes hiccups; wait and retry
                        try:
                            yt.playlistItems().update(part="snippet", body={
                                "id": s.id,
                                "snippet": {"playlistId": playlist_id,
                                            "resourceId": sn["resourceId"],
                                            "position": pos}}).execute()
                            break
                        except Exception as e:
                            m = str(e)
                            busy = any(w in m for w in ("SERVICE_UNAVAILABLE", "aborted", "backendError",
                                                        "HttpError 409", "HttpError 500", "HttpError 503"))
                            if not busy or attempt == 5:
                                raise
                            wait = 2 * (attempt + 1)
                            print(f"   YouTube was busy, waiting {wait} seconds and trying again...")
                            time.sleep(wait)
                    time.sleep(0.5)                      # a short pause between moves keeps YouTube happy
                except Exception as e:
                    msg = str(e)
                    if "manualSortRequired" in msg:
                        print("YouTube says this playlist is not set to manual order.\n"
                              "Open the playlist on youtube.com, click Sort, choose 'Manual', then run again.")
                        return moves, done, "manual"
                    if "playlistItemsNotAccessible" in msg or "forbidden" in msg.lower():
                        print("YouTube says the signed-in account isn't allowed to change this playlist.\n"
                              "Delete token.json in this folder and run Start-Setup.bat again; at the Google\n"
                              "sign-in, pick the account/channel that OWNS the playlist.")
                        return moves, done, "forbidden"
                    if "quotaExceeded" in msg or "quota" in msg.lower():
                        print("YouTube's daily limit was reached. It resets overnight; the next run continues.")
                        return moves, done, "quota"
                    print("YouTube kept refusing a move, so this run stopped early. What was done is saved,\n"
                          "and the next run picks up from there. Details: " + msg[:300])
                    return moves, done, "error"
            moves += 1
            cur.remove(s.id)
            cur.insert(pos, s.id)
            if apply and moves % 10 == 0:
                print(f"   moved {moves} of up to {budget} songs... (keep this window open)")
        done = pos + 1
    return moves, done, None


# ------------------------------------------------------------------------ main
class Tee:
    """Prints to the screen and also adds the same text to rotator_log.txt.
    Odd characters in song titles are replaced instead of crashing the window."""
    def __init__(self, stream, path):
        self.stream, self.f = stream, open(path, "a", encoding="utf-8")

    def write(self, text):
        enc = getattr(self.stream, "encoding", None) or "utf-8"
        try:
            self.stream.write(text.encode(enc, "replace").decode(enc, "replace"))
        except Exception:
            pass
        self.f.write(text)
        self.f.flush()

    def flush(self):
        try:
            self.stream.flush()
        except Exception:
            pass


def extract_id(text):
    text = (text or "").strip()
    m = re.search(r"list=([A-Za-z0-9_-]+)", text)
    return m.group(1) if m else text


def main():
    sys.stdout = Tee(sys.stdout, LOG_FILE)
    print("\n==== Run on", datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "====")
    ap = argparse.ArgumentParser()
    ap.add_argument("playlist", nargs="?", help="playlist link (optional if playlist.txt exists)")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--budget", type=int, default=180)
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--scheduled", action="store_true", help="used by the daily task: never open a browser")
    a = ap.parse_args()

    link = a.playlist
    if not link and os.path.exists(LINK_FILE):
        with open(LINK_FILE, encoding="utf-8-sig") as f:
            link = next((l.strip() for l in f if l.strip()), "")
    if not link:
        sys.exit("No playlist link found. Put your link on the first line of playlist.txt in this folder.")
    playlist_id = extract_id(link)

    yt = youtube_client(a.scheduled)
    me, owner, same = owner_check(yt, playlist_id)
    print(f"Signed in as channel: {me}")
    print(f"Playlist belongs to:  {owner}")
    if not same and not a.scheduled and os.path.exists(TOKEN):
        print("\nThose don't match, so YouTube won't let this account reorder the playlist.")
        print(f"Signing in again. In the browser, choose the account or channel named: {owner}")
        os.remove(TOKEN)
        yt = youtube_client(False)
        me, owner, same = owner_check(yt, playlist_id)
        print(f"Signed in as channel: {me}")
    if not same:
        print("\nThe signed-in channel does not own this playlist, so it can't be reordered.\n"
              f"Run Start-Setup.bat again and at the Google sign-in pick: {owner}\n"
              "(If the playlist was made by someone else, it can't be reordered. Make your own copy instead.)")
        if os.path.exists(TOKEN):
            os.remove(TOKEN)
        sys.exit(1)
    current, raw_by_id = to_songs(fetch_items(yt, playlist_id))
    playable = [s for s in current if s.playable]
    gone = [s for s in current if not s.playable]
    print(f"Found {len(playable)} songs in the playlist" + (f" (plus {len(gone)} deleted/private)." if gone else "."))

    all_mem = load_json(MEMORY, {})
    mem = None if a.reset else all_mem.get(playlist_id)
    first_run = mem is None
    known = set(mem["known"]) if mem else set()
    had_turn = set(mem["had_turn"]) if mem else set()

    def is_new(s):
        return not first_run and s.id not in known

    new = [s for s in playable if is_new(s)]
    if first_run:
        print("First run: all current songs count as already in the playlist.")
    else:
        print(f"New songs since last run: {len(new)} (they go up front).")

    target = build_order(playable, is_new, had_turn) + gone
    top = target[:min(a.budget, len(playable))]

    unsure = [s for s in top if not s.certain]
    if unsure:
        print(f"\n{len(unsure)} song(s) near the top have a guessed artist (from the channel name).")
        print('If one is wrong, add it to artists.json as  "VIDEO_ID": "Artist Name"')
        for s in unsure[:15]:
            print(f"   {s.video_id}  guessed '{s.artist}'  from  {s.title}")

    problems = check(top)
    print("\nRule check:", "passed" if not problems else "PROBLEM: " + problems[0])

    if a.apply:
        print("\nMoving songs on YouTube now. This takes a few minutes. Keep this window open.")
    used, done, stop = apply_moves(yt, playlist_id, current, target, raw_by_id, a.budget, a.apply)

    if a.apply:
        dealt = [s for s in target[:done] if s.playable]
        dealt_ids = {s.id for s in dealt}
        now_ids = {s.id for s in playable}
        known = (now_ids if first_run else (known & now_ids) | dealt_ids)
        had_turn = (had_turn & now_ids) | dealt_ids
        # once every song of an artist has had a turn, start that artist over
        by_artist = {}
        for s in playable:
            by_artist.setdefault(s.key, []).append(s.id)
        for ids in by_artist.values():
            if all(i in had_turn for i in ids):
                had_turn -= {i for i in ids if i not in dealt_ids}
        all_mem[playlist_id] = {"known": sorted(known), "had_turn": sorted(had_turn)}
        with open(MEMORY, "w", encoding="utf-8") as f:
            json.dump(all_mem, f)
        print(f"\nMoved {used} song(s). The top {done} songs are a fresh shuffle. Start listening from the top.")
    else:
        print(f"\nPreview only: {used} move(s) would be made. Add --apply to do it.")
        print("(Each real run deals its own new shuffle, so it won't match this sample exactly.)")

    print("\nFirst 25 in the new order:")
    for i, s in enumerate(target[:25], 1):
        flag = "  NEW" if is_new(s) else ""
        print(f"{i:3}. {s.artist} - {s.title}{flag}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        import traceback
        print("\nSomething went wrong. Send these lines to Claude:")
        print(traceback.format_exc())
        sys.exit(1)
