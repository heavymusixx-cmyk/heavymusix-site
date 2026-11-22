#!/usr/bin/env python3
"""
Playlist Rotator for YouTube Music  -  version 3 (rolling reshuffle, even spread)

The playlist runs as a 24/7 stream, so the WHOLE playlist gets reshuffled, a
section at a time. Each run picks up where the last one stopped and deals the
next ~180 songs (YouTube allows about 200 moves a day). When it reaches the
bottom, the next run starts a brand-new shuffle from the top. With ~700 songs
that's a full fresh pass about every 4 days.

The rules for each pass:
  * every artist plays once at the start of each pass, before any artist repeats
  * after that, each band's songs are spread EVENLY across the pass, so a band
    with lots of songs shows up regularly all the way through instead of piling
    up at the end
  * a band waits up to 20 songs before playing again (bands with lots of songs
    wait a little less so they still fit evenly), and never plays twice in a row
  * a band's songs don't repeat until all of that band's songs have played
    (each song plays once per pass; songs from late in the last pass go later)
  * NEW songs go first in the next section that gets dealt.
  * FRESH songs (added to the playlist in the last 14 days) are kept in the top 50
    spots every day for those 2 weeks, spread out, so listeners actually hear what's
    new. After that they mix in like everything else. (Owner's choice, Nov 21, 2026.)

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


GAP = 20   # a band waits up to this many songs before playing again


def artist_queues(songs, is_new, later):
    """Each band's line-up: new songs first, then songs that played early last pass,
    then songs that played late last pass (so nothing comes straight back)."""
    groups = {}
    for s in songs:
        groups.setdefault(s.key, []).append(s)
    queues = {}
    for k, g in groups.items():
        new = shuffled([s for s in g if is_new(s)])
        early = shuffled([s for s in g if not is_new(s) and s.id not in later])
        late = shuffled([s for s in g if not is_new(s) and s.id in later])
        queues[k] = new + early + late
    return queues


def build_order(songs, is_new, later, recent=(), first_round=True):
    """A fresh random order of these songs that follows the rules.
    recent = artist keys of the songs just above this stretch (oldest first).
    first_round = start with every artist once (used at the start of each pass)."""
    queues = artist_queues(songs, is_new, later)
    out = []
    history = list(recent)

    if first_round and queues:
        ks = list(queues)
        lead = shuffled([k for k in ks if is_new(queues[k][0])])   # bands with a new song go first
        rest = shuffled([k for k in ks if not is_new(queues[k][0])])
        order = lead + rest
        if len(order) > 1 and history and order[0] == history[-1]:
            order[0], order[1] = order[1], order[0]
        for k in order:
            out.append(queues[k].pop(0))
            history.append(k)

    # Even spread: each band's remaining songs get evenly spaced spots on a 0-1 line
    # (random starting offset per band). New songs get spots before 0 so they come first.
    spot = {}
    for k, q in queues.items():
        n, u = len(q), random.random()
        for j, s in enumerate(q):
            spot[s.id] = (-1.0 + j / 1000.0) if is_new(s) else (j + u) / max(n, 1)

    # How long each band waits before playing again: up to GAP songs, but a band with
    # lots of songs waits a bit less so its songs still fit evenly across the pass.
    left = sum(len(q) for q in queues.values())
    wait = {k: max(1, min(GAP, int(0.75 * left / len(q)))) for k, q in queues.items() if q}
    while left:
        active = [k for k, q in queues.items() if q]
        cap = len(active) - 1
        ok = [k for k in active
              if k not in history[len(history) - min(wait[k], cap):]] if cap > 0 else []
        ok = ok or [k for k in active if not history or k != history[-1]] or active
        k = min(ok, key=lambda k: spot[queues[k][0].id])
        out.append(queues[k].pop(0))
        history.append(k)
        left -= 1
    return out


FRESH_DAYS = 14   # how long a newly added song stays near the top
FRESH_TOP = 50    # ...within this many top spots
FRESH_MAX = 25    # at most this many fresh songs pinned at once (newest first)


def pin_fresh(target, fresh, top=FRESH_TOP):
    """Takes the planned order and moves the fresh songs into evenly spread spots in the
    top `top` positions (newest first), never next to the same band if it can be helped."""
    if not fresh:
        return target
    ids = {s.id for s in fresh}
    rest = [s for s in target if s.id not in ids]
    out = list(rest)
    step = top / len(fresh)
    for i, s in enumerate(fresh):
        pos = min(int(i * step) + 1, len(out))      # spot 1, not 0: the top song stays as dealt
        for p in (pos, pos + 1, pos - 1, pos + 2):  # dodge a same-band neighbour
            if 0 < p <= len(out) and out[p - 1].key != s.key and (p == len(out) or out[p].key != s.key):
                pos = p
                break
        out.insert(pos, s)
    return out


def check(order, recent=(), first_round=True):
    """Returns a list of problems in this stretch of songs (empty means the rules hold)."""
    problems = []
    if first_round:
        n = len({s.key for s in order})
        if len({s.key for s in order[:n]}) != n:
            problems.append("not every band played once before the first repeat")
    keys = list(recent) + [s.key for s in order]
    for i in range(len(recent), len(keys)):
        if i and keys[i] == keys[i - 1] and len(set(keys[i:])) > 1:
            problems.append(f"{order[i - len(recent)].artist} plays twice in a row")
            break
    return problems


def closest_repeat(order):
    """Smallest number of songs between two plays of the same band."""
    last, best = {}, None
    for i, s in enumerate(order):
        if s.key in last:
            d = i - last[s.key] - 1
            best = d if best is None else min(best, d)
        last[s.key] = i
    return best


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
            except Exception as e:
                # Say exactly why (e.g. "invalid_grant: Token has been expired or revoked") so the fix is obvious.
                print(f"Google refused the saved sign-in: {e}")
                creds = None
        if not creds or not creds.valid:
            if scheduled:
                print(("No saved sign-in was found (the YT_TOKEN secret is empty or not a token).\n" if not creds and not os.path.exists(TOKEN) else "") +
                      "Google sign-in is needed, but this is the automatic run so nobody can click.\n"
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
    known = set(mem.get("known", [])) if mem else set()
    now_ids = {s.id for s in playable}
    if mem and mem.get("version") == 3:
        dealt = [i for i in mem.get("dealt", []) if i in now_ids]     # this pass so far, top down
        last_pass = mem.get("last_pass", [])
        later = set(last_pass[len(last_pass) // 2:])                  # played late last pass
    else:                                                             # first run, or memory from version 2
        dealt, last_pass = [], []
        later = set(mem.get("had_turn", [])) if mem else set()

    def is_new(s):
        return not first_run and s.id not in known

    new = [s for s in playable if is_new(s)]
    today_s = datetime.date.today().isoformat()
    added = {i: d for i, d in (mem.get("added", {}) if mem else {}).items() if i in now_ids}
    for s in new:
        added.setdefault(s.id, today_s)
    cutoff = (datetime.date.today() - datetime.timedelta(days=FRESH_DAYS - 1)).isoformat()
    fresh = sorted((s for s in playable if added.get(s.id, "") >= cutoff),
                   key=lambda s: added[s.id], reverse=True)[:FRESH_MAX]
    if first_run:
        print("First run: all current songs count as already in the playlist.")
    else:
        print(f"New songs since last run: {len(new)} (they go first in today's section).")

    dealt_set = set(dealt)
    if playable and all(s.id in dealt_set for s in playable):
        print("The last pass reached the bottom of the playlist. Starting a fresh pass from the top.")
        last_pass = dealt
        later = set(last_pass[len(last_pass) // 2:])
        dealt, dealt_set = [], set()

    prefix = [s for s in current if s.playable and s.id in dealt_set]    # already done this pass
    rest = [s for s in playable if s.id not in dealt_set]
    fresh_pass = not prefix
    recent = [s.key for s in prefix[-GAP:]]
    section = build_order(rest, is_new, later, recent, first_round=fresh_pass)
    target = pin_fresh(prefix + section, fresh) + gone
    if fresh:
        print(f"Fresh songs kept in the top {FRESH_TOP} (added in the last {FRESH_DAYS} days): {len(fresh)}")
    today = section[:a.budget]

    if fresh_pass:
        print("Today's section starts at the top of the playlist (new pass).")
    else:
        print(f"This pass has already reshuffled the top {len(prefix)} of {len(playable)} songs. "
              f"Today's section starts at song {len(prefix) + 1}.")

    unsure = [s for s in today if not s.certain]
    if unsure:
        print(f"\n{len(unsure)} song(s) in today's section have a guessed artist (from the channel name).")
        print('If one is wrong, add it to artists.json as  "VIDEO_ID": "Artist Name"')
        for s in unsure[:15]:
            print(f"   {s.video_id}  guessed '{s.artist}'  from  {s.title}")

    problems = check(section, recent, first_round=fresh_pass)
    gap = closest_repeat(prefix[-GAP:] + section)
    print("\nRule check:", "passed" if not problems else "PROBLEM: " + problems[0])
    if gap is not None:
        print(f"Closest repeat of any band in the rest of this pass: {gap} songs apart.")

    if a.apply:
        print("\nMoving songs on YouTube now. This takes a few minutes. Keep this window open.")
    used, done, stop = apply_moves(yt, playlist_id, current, target, raw_by_id, a.budget, a.apply)

    if a.apply:
        dealt = [s.id for s in target[:done] if s.playable]
        dealt_ids = set(dealt)
        known = now_ids if first_run else (known & now_ids) | dealt_ids
        all_mem[playlist_id] = {"version": 3, "known": sorted(known),
                                "dealt": dealt, "last_pass": last_pass, "added": added}
        with open(MEMORY, "w", encoding="utf-8") as f:
            json.dump(all_mem, f)
        print(f"\nMoved {used} song(s). This pass has now reshuffled the top {len(dealt)} "
              f"of {len(playable)} songs.")
        if len(dealt) >= len(playable):
            print("This pass is complete. The next run starts a fresh pass from the top.")
        else:
            runs = -(-(len(playable) - len(dealt)) // max(a.budget, 1))
            print(f"About {runs} more run(s) to finish this pass.")
    else:
        print(f"\nPreview only: {used} move(s) would be made. Add --apply to do it.")
        print("(Each real run deals its own new shuffle, so it won't match this sample exactly.)")

    print(f"\nFirst 25 songs of today's section (starting at song {len(prefix) + 1}):")
    for i, s in enumerate(section[:25], len(prefix) + 1):
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
