#!/usr/bin/env python3
"""
Playlist Rotator for YouTube Music  -  version 4 (30-song band spacing across the WHOLE playlist)

Owner's rules (Nov 26-27, 2026):
  * The same band never plays within 30 songs of itself ANYWHERE in the playlist, including
    the seam where the 24/7 stream loops from the bottom back to the top. The robot aims for
    33 apart, for a safety margin.
  * Bands with too many songs for a 30-song gap (e.g. Jinjer, Job For A Cowboy, Megadeth in a
    ~750-song list) keep ALL their songs and are spread as far apart as the playlist length allows.
  * FRESH songs (added in the last 14 days) stay as near the top 50 as the spacing rule allows.
  * The robot never adds songs to HeavyMusix Radio and never removes anything, with ONE
    exception: a one-time duplicate cleanup (owner, Nov 27, 2026: "Delete duplicates and spread
    as far apart as possible"). It deletes extra copies of the same band + same song (different
    videos of one song, or the same video twice), keeps one copy, writes what it removed to
    removed_duplicates.json, then switches itself off for good.

Each run, inside YouTube's daily limit (about 180 changes):
  1. (only until it is done) the one-time duplicate cleanup, deletions first;
  2. checks the whole playlist and repairs it top first: songs that sit too close to the same
     band are moved down, the next song that fits moves up;
  3. once the rule holds everywhere, it reshuffles one block of songs among themselves (a new
     block each day, top to bottom, then round again) so the radio stays fresh, and only keeps
     a reshuffle that still passes the rule, so nothing below gets bunched.
The run log shows a rule check (repeats closer than 30, and the worst bands) before and after.

Usage:
  python playlist_rotator.py            preview only, changes nothing
  python playlist_rotator.py --apply    really change the playlist on YouTube
Options:
  --budget N   max YouTube changes per run (default 180)
  --reset      forget which songs are new
"""
import argparse, datetime, json, os, random, re, sys, time, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
MEMORY = os.path.join(HERE, "rotator_memory.json")       # which songs are new, where the block reshuffle is
OVERRIDES = os.path.join(HERE, "artists.json")           # {"videoId": "Artist"} fixes, always win
DUPES = os.path.join(HERE, "removed_duplicates.json")    # the one-time duplicate cleanup: switch + record
BANDS_FILE = os.path.join(HERE, "..", "show", "bands.json")  # the Radio Show builder's band list
SHOW_PY = os.path.join(HERE, "..", "scripts", "show.py")     # its channel-name fixes (ALIASES, UPLOADERS)
SECRETS = os.path.join(HERE, "client_secret.json")
TOKEN = os.path.join(HERE, "token.json")
LINK_FILE = os.path.join(HERE, "playlist.txt")
LOG_FILE = os.path.join(HERE, "rotator_log.txt")
SCOPES = ["https://www.googleapis.com/auth/youtube"]

RULE = 30          # owner's rule: a band never within 30 songs of itself
TARGET = 33        # what the robot aims for (safety margin)
URGENT = 1         # a crowded band gets pulled up when it has this little room left
BLOCK = 150        # songs reshuffled among themselves per run once the rule holds
FRESH_DAYS = 14    # how long a newly added song stays near the top
FRESH_TOP = 50     # ...within this many top spots (as far as the spacing rule allows)
FRESH_MAX = 25     # at most this many fresh songs pinned at once (newest first)
DUPE_MAX = 60      # safety: if the cleanup ever finds more than this, it deletes nothing and asks
GONE = ("Deleted video", "Private video")


# ------------------------------------------------------------ name matching
def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _show_tables():
    """ALIASES and UPLOADERS from scripts/show.py, read as text (never run). Empty if missing."""
    out = {"ALIASES": {}, "UPLOADERS": set()}
    try:
        import ast
        tree = ast.parse(open(SHOW_PY, encoding="utf-8").read())
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and getattr(node.targets[0], "id", "") in out:
                out[node.targets[0].id] = ast.literal_eval(node.value)
    except Exception:
        pass
    return out


_T = _show_tables()
ALIASES = dict(_T["ALIASES"])
LABELS = {  # label and aggregator channels: the band comes from the video title
    "napalm records", "nuclear blast", "nuclear blast records", "nuclear blast america", "century media records",
    "metal blade records", "prosthetic records", "season of mist", "relapse records", "spinefarm records",
    "sumerian records", "roadrunner records", "epitaph records", "fearless records", "solid state records",
    "rise records", "unfd", "sharptone records", "pure noise records", "mnrk heavy", "eone heavy", "earache records",
    "peaceville records", "svart records", "dark descent records", "20 buck spin", "profound lore records",
    "willowtip records", "unique leader records", "transcending obscurity", "listenable records", "agonia records",
    "inside out music", "insideoutmusictv", "frontiers music srl", "afm records", "massacre records", "steamhammer",
    "spv", "reigning phoenix music", "atomic fire records", "candlelight records", "candlelight", "osmose productions",
    "hammerheart records", "black lion records", "m-theory audio", "silver lining music", "better noise music",
    "eleven seven music", "cleopatra records", "magnetic eye records", "argonauta records", "debemur morti",
    "debemur morti productions", "les acteurs de l'ombre", "pelagic records", "metal injection", "metalsucks",
    "metal hammer", "revolver", "loudwire", "decibel magazine", "no clean singing", "brutal assault",
    "bloodblast distribution", "blood blast distribution", "metalsinpantalones", "agnt thrasher", "ola englund",
    "banger tv", "bangertv", "the pit", "metal archives", "metalheads", "thrash metal", "death metal",
}
LABELS |= {u.lower() for u in _T["UPLOADERS"]}
FAN_CHANNELS = {"metalsinpantalones", "agnt thrasher", "ola englund", "metal archives", "metalheads",
                "thrash metal", "death metal", "the pit", "banger tv", "bangertv"}
FEAT = re.compile(r"\s*[\(\[]?\s*\b(feat\.?|ft\.?|featuring)\s.*$", re.I)


def plain(s):
    """lower case, no accents, & -> and."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().replace("&", " and ").replace("’", "'")


def band_key(name):
    """Matching key for a band: ignores case, accents, punctuation, 'The', '- Topic', 'VEVO',
    'Official', 'feat.', spaces, and a trailing 'Band' / 'Metal Band'."""
    s = ALIASES.get((name or "").strip(), name or "")
    s = FEAT.sub("", s)
    s = re.sub(r"\s*-\s*topic\s*$", "", s, flags=re.I)
    s = plain(s)
    s = re.sub(r"vevo\s*$", "", s)
    s = re.sub(r"\bofficial\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    s = re.sub(r"^the\s+", "", s)
    s = re.sub(r"\s+(metal band|band)$", "", s) if len(s.split()) > 1 else s
    k = s.replace(" ", "")
    for w in ("official",):
        if k.startswith(w) and len(k) > len(w) + 2:
            k = k[len(w):]
        if k.endswith(w) and len(k) > len(w) + 2:
            k = k[:-len(w)]
    return k


def clean_artist(name):
    name = ALIASES.get((name or "").strip(), name or "")
    name = FEAT.sub("", name.strip())
    name = re.sub(r"\s*-\s*Topic$", "", name, flags=re.I)
    name = re.sub(r"\s*VEVO$", "", name)
    return name.strip(" \"'“”") or name


def _known_bands():
    out = {}
    for v in load_json(BANDS_FILE, {}).values():
        n = (v or {}).get("name") if isinstance(v, dict) else None
        if n and len(band_key(n)) >= 3:
            out[band_key(n)] = n
    for a, n in ALIASES.items():
        out.setdefault(band_key(n), n)
    return out


KNOWN = _known_bands()


def is_label(channel):
    c = plain(re.sub(r"\s*-\s*Topic$", "", channel or "", flags=re.I)).strip()
    if c in LABELS:
        return True
    return bool(re.search(r"\b(records|recordings|music group|entertainment|productions)\b", c))


DASH = re.compile(r"\s[-–—]\s")


def split_title(title):
    """(left part, rest) of 'Band - Song', or 'BAND "Song"', else (None, title)."""
    t = re.sub(r"\s*[|｜].*$", "", title or "").strip()
    m = DASH.search(t)
    if m and m.start() > 0:
        return t[:m.start()].strip(), t[m.end():].strip()
    m = re.match(r'^\s*([^"“]{2,}?)\s+["“](.+?)["”]', t)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None, t


def guess_artist(title, channel, override=None):
    """Returns (artist, certain). Your fix > '- Topic' channel > title on label channels >
    title/channel, checked against the Radio Show builder's band list."""
    if override:
        return override, True
    channel = channel or ""
    if re.search(r"-\s*Topic$", channel, re.I) and not is_label(channel):
        return clean_artist(channel), True
    left, _ = split_title(title)
    if is_label(channel) or not channel:
        if left:
            k = band_key(left)
            return KNOWN.get(k, clean_artist(left)), True
        tk = band_key(title)
        for k in sorted(KNOWN, key=len, reverse=True):          # 'JINJER Pisces' style titles
            if len(k) >= 4 and tk.startswith(k):
                return KNOWN[k], True
        return (clean_artist(channel), False) if channel else ("Unknown", False)
    ck = band_key(channel)
    if left:
        lk = band_key(left)
        if lk == ck:
            return KNOWN.get(ck, clean_artist(channel)), True
        if lk in KNOWN:
            return KNOWN[lk], True
        if ck in KNOWN:                                         # band channel, 'Song - Official Video'
            return KNOWN[ck], True
        return clean_artist(left), True
    return KNOWN.get(ck, clean_artist(channel)), ck in KNOWN


# Tags that don't make a different recording. Anything with 'live' in it always stays (a live
# version is a different track), and so does anything not listed here (acoustic, demo, remix...).
NOISE_WORDS = re.compile(
    r"\b(official|video|videoclip|clip|lyrics?|audio|visuali[sz]er|hd|hq|4k|1080p|explicit|uncensored|"
    r"remaster(ed)?|\d{4}\s+remix|remixed|full song|premiere|single|stream|album track|bonus track|from the album)\b", re.I)
BRACKETS = re.compile(r"\s*[\(\[\{]([^\)\]\}]*)[\)\]\}]")


def song_name(title, artist):
    """The song part of a title with tags like (Official Video), [HD], (2004 Remaster) removed."""
    left, rest = split_title(title)
    t = rest if left is not None and band_key(left) == band_key(artist) else (title or "")
    t = re.sub(r"\s*[|｜].*$", "", t)
    if band_key(t[:len(artist)]) == band_key(artist) and len(t) > len(artist) + 1:
        t = t[len(artist):].lstrip(" -–—:")                        # 'JINJER Pisces'
    t = BRACKETS.sub(lambda m: "" if NOISE_WORDS.search(m.group(1)) and not re.search(r"\blive\b", m.group(1), re.I)
                     else m.group(0), t)
    parts = DASH.split(t)                                       # 'Song - Official Music Video'
    t = parts[0] + "".join(" - " + p for p in parts[1:]
                           if not (NOISE_WORDS.search(p) and not re.search(r"\blive\b", p, re.I)))
    return t.strip(" \"'“”").strip() or (title or "")


def song_key(name):
    return re.sub(r"[^a-z0-9]+", "", plain(name))


def loose_song_key(name):
    """Looser: drops every bracket and 'feat.' part. Only used to LIST possible duplicates."""
    t = BRACKETS.sub("", name)
    t = FEAT.sub("", t)
    return song_key(t)


class Song:
    def __init__(self, item_id, video_id, title, channel, override=None, playable=True):
        self.id = item_id
        self.video_id = video_id
        self.raw_title = title or ""
        self.channel = channel or ""
        self.playable = playable
        self.artist, self.certain = guess_artist(title, channel, override)
        self.key = band_key(self.artist) or plain(self.artist)
        self.title = song_name(title, self.artist)
        self.song = song_key(self.title)

    def official(self):
        """0 = the band's own channel, its '- Topic' audio or a label; 1 = a fan or other upload."""
        c = self.channel
        if re.search(r"-\s*Topic$", c, re.I) or band_key(c) == self.key:
            return 0
        if is_label(c) and plain(c).strip() not in FAN_CHANNELS:
            return 0
        return 1


# ------------------------------------------------------------ the spacing rule
def max_gap(count, length):
    """The widest spacing (songs in between) a band with `count` songs can get in a looping
    playlist of `length` songs."""
    return length - 1 if count <= 1 else max(0, length // count - 1)


def band_gaps(songs, target=TARGET):
    counts = {}
    for s in songs:
        counts[s.key] = counts.get(s.key, 0) + 1
    n = len(songs)
    return {k: min(target, max_gap(c, n)) for k, c in counts.items()}, counts


def repeats(order):
    """Every pair of back-to-back plays of the same band, incl. the loop from bottom to top:
    (band key, songs in between, position of the second play)."""
    n, pos = len(order), {}
    for i, s in enumerate(order):
        pos.setdefault(s.key, []).append(i)
    out = []
    for k, ps in pos.items():
        if len(ps) < 2:
            continue
        for a, b in zip(ps, ps[1:]):
            out.append((k, b - a - 1, b))
        out.append((k, n - ps[-1] - 1 + ps[0], ps[0]))          # the seam
    return out


def rule_report(order, rule=RULE):
    """Counts repeats closer than `rule`. 'avoidable' = those from bands that have room for a
    `rule` gap; crowded bands (too many songs for it) are listed with the widest spacing their
    song count allows."""
    gaps, counts = band_gaps(order, rule)
    names = {}
    for s in order:
        names.setdefault(s.key, s.artist)
    close, avoidable, per = 0, 0, {}
    for k, d, _ in repeats(order):
        if d < rule:
            close += 1
            m = max_gap(counts[k], len(order))
            p = per.setdefault(k, [0, d, counts[k], m])
            p[0] += 1
            p[1] = min(p[1], d)
            if m >= rule:
                avoidable += 1
    worst = sorted(per.items(), key=lambda kv: (kv[1][3] < rule, kv[1][1] - min(kv[1][3], rule), -kv[1][0]))
    return {"close": close, "avoidable": avoidable,
            "worst": [(names[k], c, d, n, m) for k, (c, d, n, m) in worst]}


def print_report(label, rep, top=12):
    print(f"Rule check {label}: {rep['close']} band repeat(s) closer than {RULE} songs; "
          f"{rep['avoidable']} of them from bands that have room for {RULE} (the rest are from bands "
          f"with too many songs for a {RULE}-song gap).")
    for name, c, d, n, m in rep["worst"][:top]:
        extra = f" ({n} songs: the most possible is {m})" if m < RULE else ""
        print(f"   {name}: {c} close repeat(s), closest {d} songs apart{extra}")


def _ok_at(order, i, gaps):
    """Is the song at i far enough from its band's other songs (incl. the loop)?"""
    n, k = len(order), order[i].key
    g = min(gaps.get(k, 0), n - 1)
    for d in range(1, g + 1):
        if order[(i + d) % n].key == k or order[(i - d) % n].key == k:
            return False
    return True


def polish(order, gaps, fixed):
    """Last touch: a song still too close to its band swaps with another song where both fit.
    Songs of crowded bands (fixed spots) never move here."""
    order = list(order)
    n = len(order)
    for _ in range(3):
        bad = [i for i in range(n) if order[i].key not in fixed and not _ok_at(order, i, gaps)]
        if not bad:
            break
        for i in bad:
            if _ok_at(order, i, gaps):
                continue
            for j in sorted(range(n), key=lambda j: abs(j - i)):
                if j == i or order[j].key in fixed or order[j].key == order[i].key:
                    continue
                order[i], order[j] = order[j], order[i]
                if _ok_at(order, i, gaps) and _ok_at(order, j, gaps):
                    break
                order[i], order[j] = order[j], order[i]
    return order


def crowded(counts, n, target=TARGET):
    """Bands with too many songs to be spaced `target` apart with room to spare. They get
    evenly spread fixed spots (as far apart as the playlist length allows)."""
    return {k for k, c in counts.items() if c >= 2 and c * (target + 1) * 1.5 > n}


def _slots(n, c, offset):
    step = n / c
    return [int(offset + j * step) % n for j in range(c)]


def space_out(seq, gaps, wrap=True, offsets=None):
    """Keeps `seq` in order as much as possible while spacing each band at least gaps[band]
    songs apart (incl. the loop from bottom to top).
      * Crowded bands (too many songs for the target gap) get evenly spaced spots first, each
        band's songs in the order they come in `seq`; offsets[band] keeps a band's spots the
        same from day to day (filled in when missing).
      * Every other song keeps its order; one that would land too close to its band waits and
        the next song that fits moves up. Never fails: if nothing fits, the band heard longest
        ago goes next."""
    n = len(seq)
    if offsets is None:
        offsets = {}
    counts, where = {}, {}
    for i, s in enumerate(seq):
        counts[s.key] = counts.get(s.key, 0) + 1
        where.setdefault(s.key, []).append(i)
    big = crowded(counts, n)
    out = [None] * n
    for k in sorted(big, key=lambda k: (-counts[k], k)):
        c, step = counts[k], n / counts[k]
        off = offsets.get(k)
        if not isinstance(off, int) or not 0 <= off < step:
            best = None
            for o in range(max(1, int(step))):          # clear of other crowded bands, then the
                sl = _slots(n, c, o)                     # offset closest to where the songs are now
                clash = sum(1 for q in sl for x in (q - 1, q, q + 1) if 0 <= x < n and out[x] is not None)
                cost = clash * n * c + sum(abs(a - b) for a, b in zip(sl, where[k]))
                if best is None or cost < best[0]:
                    best = (cost, o)
            off = best[1]
        offsets[k] = off
        spots = []
        for q in _slots(n, c, off):
            for d in range(n):                          # nearest free spot (other crowded bands)
                hit = next((x for x in (q + d, q - d) if 0 <= x < n and out[x] is None and x not in spots), None)
                if hit is not None:
                    spots.append(hit)
                    break
        for p, i in zip(sorted(spots), where[k]):      # the band's songs keep their order
            out[p] = seq[i]
    rest = [s for s in seq if s.key not in big]
    rem = {}
    for s in rest:
        rem[s.key] = rem.get(s.key, 0) + 1
    free = [p for p in range(n) if out[p] is None]
    last, first = {}, {}
    for p in free:
        left = n - p

        def fits(k):
            g = gaps.get(k, 0)
            if k in last and p - last[k] - 1 < g:
                return False
            if wrap and k in first and (n - 1 - p) + first[k] < g:
                return False
            return True

        pick = None
        urgent = sorted((left - ((r - 1) * (gaps.get(k, 0) + 1) + 1), k) for k, r in rem.items() if r > 0)
        urgent = [x for x in urgent if x[0] <= URGENT and fits(x[1])]
        if urgent:
            k = urgent[0][1]
            pick = next(i for i, s in enumerate(rest) if s.key == k)
        else:
            pick = next((i for i, s in enumerate(rest) if fits(s.key)), None)
        if pick is None:                                # nothing fits: least-bad choice
            pick = max(range(len(rest)), key=lambda i: (p - last.get(rest[i].key, -10 ** 6), -i))
        s = rest.pop(pick)
        out[p] = s
        rem[s.key] -= 1
        last[s.key] = p
        first.setdefault(s.key, p)
    return polish(out, gaps, big)


def pin_fresh(order, fresh, top=FRESH_TOP):
    """Puts fresh songs (newest first) in evenly spread spots in the top `top` of the order;
    space_out() then lets any that would land too close to their band slide down."""
    if not fresh:
        return list(order)
    ids = {s.id for s in fresh}
    out = [s for s in order if s.id not in ids]
    step = top / len(fresh)
    for i, s in enumerate(fresh):
        out.insert(min(int(i * step) + 1, len(out)), s)
    return out


def count_moves(current_ids, target_ids):
    """How many YouTube moves apply_moves() needs to turn current into target (top down)."""
    cur, moves = list(current_ids), 0
    for pos, i in enumerate(target_ids):
        if cur[pos] != i:
            moves += 1
            cur.remove(i)
            cur.insert(pos, i)
    return moves


def plan(playable, fresh, block_start, budget, rng, offsets=None):
    """The order to aim for: the current order repaired for spacing (fresh songs pinned near the
    top). If that needs no moves, one block is reshuffled among themselves instead, kept only
    if the result still passes the rule. Returns (target, block (start, size) or None)."""
    gaps, _ = band_gaps(playable)
    offsets = {} if offsets is None else offsets
    target = space_out(pin_fresh(playable, fresh), gaps, offsets=offsets)
    ids = [s.id for s in playable]
    if count_moves(ids, [s.id for s in target]) or len(playable) < 3 or budget < 2:
        return target, None
    base = rule_report(target)
    n = len(playable)
    start = block_start if 0 <= block_start < n else 0
    size = min(BLOCK, budget, n - start)
    for _ in range(8):
        if size < 2:
            break
        block = playable[start:start + size]
        rng.shuffle(block)
        cand = space_out(pin_fresh(playable[:start] + block + playable[start + size:], fresh), gaps,
                         offsets=dict(offsets))
        rep = rule_report(cand)
        m = count_moves(ids, [s.id for s in cand])
        if rep["avoidable"] <= base["avoidable"] and rep["close"] <= base["close"] and m <= budget:
            return cand, (start, size)
        size = int(size * 0.7)
    return target, None


# ------------------------------------------------------------ duplicate songs
def find_duplicates(songs):
    """Groups copies of the same song: the same video twice, or the same band + the same song
    name (tags like (Official Video), [HD], (2004 Remaster) ignored; live versions are their own
    song). Keeps ONE: the band's own / '- Topic' / label upload over a fan upload, then the one
    higher in the playlist. Returns (remove, keep_for, maybe): maybe = looser matches that are
    NOT removed, listed for the owner."""
    idx = {s.id: i for i, s in enumerate(songs)}
    parent = list(range(len(songs)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    seen = {}
    for i, s in enumerate(songs):
        if not s.playable:
            continue
        for key in (("v", s.video_id) if s.video_id else None,
                    ("s", s.key, s.song) if len(s.song) >= 2 and s.key else None):
            if key is None:
                continue
            if key in seen:
                parent[find(i)] = find(seen[key])
            else:
                seen[key] = i
    groups = {}
    for i, s in enumerate(songs):
        if s.playable:
            groups.setdefault(find(i), []).append(s)
    remove, keep_for = [], {}
    for g in groups.values():
        if len(g) < 2:
            continue
        g.sort(key=lambda s: (s.official(), idx[s.id]))
        for s in g[1:]:
            remove.append(s)
            keep_for[s.id] = g[0]
    remove.sort(key=lambda s: idx[s.id])
    gone = {s.id for s in remove}
    loose = {}
    for s in songs:
        if s.playable and s.id not in gone:
            loose.setdefault((s.key, loose_song_key(s.title)), []).append(s)
    maybe = [g for k, g in loose.items() if len(g) > 1 and len(k[1]) >= 2]
    return remove, keep_for, maybe


def dupe_cleanup(yt, current, apply, budget):
    """The ONE-TIME duplicate cleanup. Runs only while removed_duplicates.json says 'pending'.
    Deletes the extra copies (at most `budget` today), records each one, and switches itself to
    'done' when nothing is left. Quota or errors stop it safely; the next run resumes.
    Returns how many YouTube deletions it made."""
    state = load_json(DUPES, None)
    if not isinstance(state, dict) or state.get("status") != "pending":
        return 0
    state.setdefault("removed", [])
    remove, keep_for, maybe = find_duplicates(current)
    pos = {s.id: i + 1 for i, s in enumerate(current)}
    print(f"\nOne-time duplicate cleanup: {len(remove)} extra cop{'y' if len(remove) == 1 else 'ies'} found.")
    for s in remove:
        k = keep_for[s.id]
        print(f"   remove: {s.artist} - {s.title} (song {pos[s.id]}, {s.video_id}); "
              f"keeping song {pos[k.id]} ({k.video_id}, {k.channel or 'unknown channel'})")
    state["possible_duplicates_kept"] = [
        [{"band": s.artist, "song": s.title, "videoId": s.video_id, "position": pos[s.id]} for s in g] for g in maybe]
    if maybe:
        print(f"   {len(maybe)} possible duplicate(s) KEPT (not sure they are the same recording):")
        for g in maybe:
            print("     " + "  |  ".join(f"{s.artist} - {s.raw_title} (song {pos[s.id]})" for s in g))
    if not apply:
        print("   (preview: nothing deleted)")
        return 0
    if len(remove) > DUPE_MAX:
        state["status"] = "too_many"
        state["note"] = (f"Found {len(remove)} duplicates, more than the safety limit of {DUPE_MAX}, so nothing "
                         "was deleted. Check the list in the run log, then set status back to pending to run it.")
        print("   " + state["note"])
        _save_dupes(state)
        return 0
    made, stop = 0, None
    today = datetime.date.today().isoformat()
    for s in remove:
        if made >= budget:
            stop = "budget"
            break
        try:
            _retry(lambda: yt.playlistItems().delete(id=s.id).execute())
            made += 1
            note = ""
        except Exception as e:
            msg = str(e)
            if "notFound" in msg or "HttpError 404" in msg:
                note = " (was already gone)"
            elif "quota" in msg.lower():
                stop = "quota"
                break
            else:
                state["errors"] = state.get("errors", 0) + 1
                print("   YouTube refused a deletion, so the cleanup stopped for today. Details: " + msg[:300])
                stop = "error"
                break
        k = keep_for[s.id]
        state["removed"].append({"band": s.artist, "song": s.title, "title": s.raw_title, "videoId": s.video_id,
                                 "channel": s.channel, "position": pos[s.id], "kept_videoId": k.video_id,
                                 "date": today})
        print(f"   removed: {s.artist} - {s.title} (was song {pos[s.id]}, {s.video_id}){note}")
        _save_dupes(state)                         # saved after every deletion, so nothing is forgotten
    if stop is None:
        state["status"] = "done"
        state["finished"] = today
        print(f"   Duplicate cleanup finished: {len(state['removed'])} removed in all. It is now switched off for good.")
    elif stop == "quota":
        print("   YouTube's daily limit was reached; the cleanup carries on next run.")
    elif stop == "budget":
        print("   Today's change budget is used; the cleanup carries on next run.")
    if state.get("errors", 0) >= 3 and state["status"] == "pending":
        state["status"] = "stopped"
        state["note"] = "Stopped after YouTube refused deletions on 3 runs. Ask Claude to look at the run log."
        print("   " + state["note"])
    _save_dupes(state)
    return made


def _save_dupes(state):
    with open(DUPES, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1, ensure_ascii=False)


def _retry(call):
    for attempt in range(6):                  # YouTube sometimes hiccups; wait and retry
        try:
            return call()
        except Exception as e:
            m = str(e)
            busy = any(w in m for w in ("SERVICE_UNAVAILABLE", "aborted", "backendError",
                                        "HttpError 409", "HttpError 500", "HttpError 503"))
            if not busy or attempt == 5:
                raise
            wait = 2 * (attempt + 1)
            print(f"   YouTube was busy, waiting {wait} seconds and trying again...")
            time.sleep(wait)


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
                print(f"Google refused the saved sign-in: {e}")
                creds = None
        if not creds or not creds.valid:
            if scheduled:
                print(("No saved sign-in was found (the YT_TOKEN secret is empty or not a token).\n" if not creds and not os.path.exists(TOKEN) else "") +
                      "Google sign-in is needed, but this is the automatic run so nobody can click.\n"
                      "Double-click Start-Setup.bat once to sign in again. Tip: in Google Cloud, the\n"
                      "OAuth consent screen must say 'In production' (Publish App) or sign-in expires every 7 days.")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(SECRETS, SCOPES)
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
    Returns (moves made, how many top spots now match the plan, stop reason, order now)."""
    cur = [s.id for s in current]
    moves = done = 0
    for pos, s in enumerate(target):
        if not s.playable:          # deleted/private videos are left at the bottom, never moved
            return moves, done, None, cur
        if cur[pos] != s.id:
            if moves >= budget:
                return moves, done, "budget", cur
            if apply:
                sn = raw_by_id[s.id]["snippet"]
                try:
                    _retry(lambda: yt.playlistItems().update(part="snippet", body={
                        "id": s.id,
                        "snippet": {"playlistId": playlist_id,
                                    "resourceId": sn["resourceId"],
                                    "position": pos}}).execute())
                    time.sleep(0.5)                      # a short pause between moves keeps YouTube happy
                except Exception as e:
                    msg = str(e)
                    if "manualSortRequired" in msg:
                        print("YouTube says this playlist is not set to manual order.\n"
                              "Open the playlist on youtube.com, click Sort, choose 'Manual', then run again.")
                        return moves, done, "manual", cur
                    if "playlistItemsNotAccessible" in msg or "forbidden" in msg.lower():
                        print("YouTube says the signed-in account isn't allowed to change this playlist.\n"
                              "Delete token.json in this folder and run Start-Setup.bat again; at the Google\n"
                              "sign-in, pick the account/channel that OWNS the playlist.")
                        return moves, done, "forbidden", cur
                    if "quotaExceeded" in msg or "quota" in msg.lower():
                        print("YouTube's daily limit was reached. It resets overnight; the next run continues.")
                        return moves, done, "quota", cur
                    print("YouTube kept refusing a move, so this run stopped early. What was done is kept,\n"
                          "and the next run picks up from there. Details: " + msg[:300])
                    return moves, done, "error", cur
            moves += 1
            cur.remove(s.id)
            cur.insert(pos, s.id)
            if apply and moves % 20 == 0:
                print(f"   moved {moves} of up to {budget} songs...")
        done = pos + 1
    return moves, done, None, cur


# ------------------------------------------------------------------------ main
class Tee:
    """Prints to the screen and also adds the same text to rotator_log.txt."""
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
    print("\n==== Run on", datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "(rotator v4) ====")
    ap = argparse.ArgumentParser()
    ap.add_argument("playlist", nargs="?", help="playlist link (optional if playlist.txt exists)")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--budget", type=int, default=180)
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--scheduled", action="store_true", help="used by the daily task: never open a browser")
    a = ap.parse_args()
    budget = max(0, a.budget)

    link = a.playlist
    if not link and os.path.exists(LINK_FILE):
        with open(LINK_FILE, encoding="utf-8-sig") as f:
            link = next((l.strip() for l in f if l.strip()), "")
    if not link:
        sys.exit("No playlist link found. Put your link on the first line of playlist.txt in this folder.")
    playlist_id = extract_id(link)
    roots_file = os.path.join(HERE, "roots_playlist.txt")
    if os.path.exists(roots_file) and open(roots_file, encoding="utf-8").read().strip() == playlist_id:
        sys.exit("Refusing: that is the private HeavyMusix Roots playlist, which is never reshuffled.")

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
        print("\nThe signed-in channel does not own this playlist, so it can't be changed.\n"
              f"Run Start-Setup.bat again and at the Google sign-in pick: {owner}")
        if os.path.exists(TOKEN):
            os.remove(TOKEN)
        sys.exit(1)

    current, raw_by_id = to_songs(fetch_items(yt, playlist_id))
    playable = [s for s in current if s.playable]
    print(f"Found {len(playable)} songs in the playlist" +
          (f" (plus {len(current) - len(playable)} deleted/private)." if len(current) > len(playable) else "."))
    print_report("BEFORE", rule_report(playable))

    # 1. one-time duplicate cleanup (deletions first: they use the same daily limit)
    deleted = 0
    try:
        deleted = dupe_cleanup(yt, current, a.apply, budget)
    except Exception as e:                       # never let the cleanup stop the reshuffle
        print("   The duplicate cleanup hit a problem and was skipped today: " + str(e)[:300])
    if deleted:
        budget -= deleted
        current, raw_by_id = to_songs(fetch_items(yt, playlist_id))
        playable = [s for s in current if s.playable]
        print(f"Now {len(playable)} songs in the playlist.")
    gone = [s for s in current if not s.playable]

    # 2. new and fresh songs
    all_mem = load_json(MEMORY, {})
    mem = None if a.reset else all_mem.get(playlist_id)
    first_run = mem is None
    known = set(mem.get("known", [])) if mem else set()
    now_ids = {s.id for s in playable}
    new = [] if first_run else [s for s in playable if s.id not in known]
    today_s = datetime.date.today().isoformat()
    added = {i: d for i, d in (mem.get("added", {}) if mem else {}).items() if i in now_ids}
    for s in new:
        added.setdefault(s.id, today_s)
    cutoff = (datetime.date.today() - datetime.timedelta(days=FRESH_DAYS - 1)).isoformat()
    fresh = sorted((s for s in playable if added.get(s.id, "") >= cutoff),
                   key=lambda s: added[s.id], reverse=True)[:FRESH_MAX]
    print(f"New songs since last run: {len(new)}. Fresh songs kept near the top {FRESH_TOP}: {len(fresh)}.")
    block_start = mem.get("block", 0) if mem and mem.get("version") == 4 else 0
    offsets = dict(mem.get("spots", {})) if mem and mem.get("version") == 4 else {}

    # 3. the plan for the whole playlist, then the moves (top first)
    target, block = plan(playable, fresh, block_start, budget, random.Random(), offsets)
    if block:
        print(f"The spacing rule already holds everywhere, so today songs {block[0] + 1}-{block[0] + block[1]} "
              "are reshuffled among themselves.")
    need = count_moves([s.id for s in current], [s.id for s in target + gone])
    print(f"Moves needed for the plan: {need} (today's limit: {budget}).")
    print_report("PLAN (when every move is done)", rule_report(target), top=5)

    unsure = [s for s in playable if not s.certain]
    if unsure:
        print(f"\n{len(unsure)} song(s) have a guessed band (from the channel name). To fix one, add it to "
              'artists.json as  "VIDEO_ID": "Band Name"')
        for s in unsure[:10]:
            print(f"   {s.video_id}  guessed '{s.artist}'  from  {s.raw_title}")

    if a.apply:
        print("\nMoving songs on YouTube now.")
    used, done, stop, now = apply_moves(yt, playlist_id, current, target + gone, raw_by_id, budget, a.apply)
    by_id = {s.id: s for s in current}
    after = [by_id[i] for i in now if by_id[i].playable]
    print_report("AFTER today's moves" if a.apply else "AFTER today's moves (preview)", rule_report(after))
    left = need - used
    if left > 0:
        print(f"About {-(-left // max(min(a.budget, 180), 1))} more daily run(s) to finish the repair "
              f"({left} moves left).")

    if a.apply:
        if block and stop is None:
            block_start = block[0] + block[1]
            if block_start >= len(playable):
                block_start = 0
        all_mem[playlist_id] = {"version": 4, "known": sorted(now_ids), "added": added, "block": block_start,
                                "spots": offsets}
        with open(MEMORY, "w", encoding="utf-8") as f:
            json.dump(all_mem, f)
        print(f"\nMoved {used} song(s)" + (f", deleted {deleted} duplicate(s)" if deleted else "") + ".")
    else:
        print(f"\nPreview only: {used} move(s) would be made. Add --apply to do it.")

    print("\nTop 25 songs after today's moves:")
    for i, s in enumerate(after[:25], 1):
        print(f"{i:3}. {s.artist} - {s.title}{'  FRESH' if s in fresh else ''}")


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
