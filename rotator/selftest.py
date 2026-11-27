"""Self-test for playlist_rotator.py (version 4). The daily workflow runs this first; if it fails,
the real playlist is never touched. Uses a fake YouTube (random 'busy' errors, a daily limit) and:
  * band and song matching (case, accents, 'The', '- Topic', VEVO, Official, feat., label channels)
  * a 700-song playlist with a 70-song band, label channels and duplicates in several forms
  * the one-time duplicate cleanup: removes only true duplicates, keeps the official copy,
    resumes after a quota stop, never runs twice
  * an error stop in the middle of the moves, fresh songs, the loop seam, tiny playlists
"""
import sys, json, os, random, datetime, types, io, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import playlist_rotator as R

BAD = []
def expect(ok, what):
    if not ok:
        BAD.append(what)
        print("   FAIL:", what)

# ---------------------------------------------------------------- matching
bk = R.band_key
expect(bk("The Black Dahlia Murder") == bk("Black Dahlia Murder") == bk("BLACK DAHLIA MURDER - Topic"), "'The' / Topic / case")
expect(bk("Motörhead") == bk("Motorhead") and bk("MegadethVEVO") == bk("Megadeth"), "accents / VEVO")
expect(bk("Jinjer Metal Band") == bk("JINJER") and bk("Spiritbox Official") == bk("Spiritbox"), "Metal Band / Official")
expect(bk("Gojira feat. Someone") == bk("Gojira") and bk("Mötley Crüe") == bk("Motley Crue"), "feat. / umlauts")
expect(bk("Exodus") != bk("Exhorder") and bk("Death") != bk("Death Angel"), "different bands stay different")
g = R.guess_artist
expect(g("JINJER - Pisces (Official Video) | Napalm Records", "Napalm Records")[0].lower() == "jinjer", "band from title on label channel")
expect(bk(g('ARCH ENEMY "The Eagle Flies Alone" (OFFICIAL VIDEO)', "Century Media Records")[0]) == bk("Arch Enemy"), 'BAND "Song" on label channel')
expect(bk(g("Pisces", "Jinjer - Topic")[0]) == bk("Jinjer"), "Topic channel")
expect(bk(g("Symphony Of Destruction", "MegadethVEVO")[0]) == bk("Megadeth"), "VEVO channel")
sn = lambda t, a: R.song_key(R.song_name(t, a))
expect(sn("Jinjer - Pisces (Official Video)", "Jinjer") == sn("Pisces", "Jinjer") == sn("JINJER - Pisces [HD] | Napalm Records", "Jinjer"), "song tags ignored")
expect(sn("Megadeth - Peace Sells (2004 Remaster)", "Megadeth") == sn("Peace Sells", "Megadeth") == sn("Peace Sells - Remastered 2004", "Megadeth"), "remaster tags ignored")
expect(sn("Pisces (Live Session)", "Jinjer") != sn("Pisces", "Jinjer") and sn("Waltz (Live)", "Jinjer") != sn("Waltz", "Jinjer"), "live versions are different songs")
expect(sn("Song (Acoustic)", "X") != sn("Song", "X"), "acoustic version is a different song")

# ---------------------------------------------------------------- fake YouTube
class Quota(Exception): pass

class FakeYT:
    def __init__(self, items, limit=10 ** 9, fail_rate=0.03):
        self.items, self.limit, self.fail_rate = items, limit, fail_rate
        self.used = self.moves = self.deletes = 0
        self.break_after = None                       # raise a hard error after this many moves
    def channels(self): return types.SimpleNamespace(list=lambda **k: types.SimpleNamespace(execute=lambda: {"items": [{"id": "me", "snippet": {"title": "HeavyMusix"}}]}))
    def playlists(self): return types.SimpleNamespace(list=lambda **k: types.SimpleNamespace(execute=lambda: {"items": [{"snippet": {"channelTitle": "HeavyMusix", "channelId": "me"}}]}))
    def _spend(self):
        if self.used >= self.limit:
            raise Quota("HttpError 403 quotaExceeded")
        if random.random() < self.fail_rate:
            raise Exception("HttpError 503 SERVICE_UNAVAILABLE")
        self.used += 1
    def playlistItems(self):
        yt = self
        def lst(part, playlistId, maxResults, pageToken=None):
            st = int(pageToken or 0)
            r = {"items": yt.items[st:st + maxResults]}
            if st + maxResults < len(yt.items): r["nextPageToken"] = str(st + maxResults)
            return types.SimpleNamespace(execute=lambda: r)
        def upd(part, body):
            def ex():
                if yt.break_after is not None and yt.moves >= yt.break_after:
                    raise Exception("HttpError 400 something odd")
                yt._spend()
                i = next(k for k, x in enumerate(yt.items) if x["id"] == body["id"])
                it = yt.items.pop(i); yt.items.insert(body["snippet"]["position"], it); yt.moves += 1
            return types.SimpleNamespace(execute=ex)
        def dele(id):
            def ex():
                yt._spend()
                i = next(k for k, x in enumerate(yt.items) if x["id"] == id)
                yt.items.pop(i); yt.deletes += 1
            return types.SimpleNamespace(execute=ex)
        return types.SimpleNamespace(list=lst, update=upd, delete=dele)

def mk(iid, title, channel="", vid=None):
    return {"id": f"item{iid}", "snippet": {"title": title, "videoOwnerChannelTitle": channel,
            "resourceId": {"kind": "youtube#video", "videoId": vid or f"v{iid}"}}}

def build_playlist():
    """700 items: Bigband 70 songs (half from its label), 40 bands of 4-16 songs, singles,
    label and Topic channels, plus 6 true duplicates and 3 look-alikes that must stay."""
    items, n = [], 0
    def add(title, ch="", vid=None):
        nonlocal n
        items.append(mk(n, title, ch, vid)); n += 1
    for i in range(70):
        if i % 2: add(f"BIGBAND - Track {i} (Official Video) | Napalm Records", "Napalm Records")
        else: add(f"Track {i}", "Bigband - Topic")
    for b in range(40):
        for j in range(4 + b % 13):
            add(f"The Band{b} - Song {j}", f"Band{b}VEVO" if b % 3 == 0 else f"Band{b}")
    while len(items) < 691:
        add(f"Single{len(items)} - Only Song", f"Single{len(items)}")
    # true duplicates (6): each must lose exactly one copy
    add("Band1 - Song 0 (Lyric Video)", "Some Fan Channel")                  # lyric video, fan upload
    add("Song 0", "Band2 - Topic")                                            # Topic audio of an existing song
    add("BIGBAND - Track 0 [HD]", "MetalSinPantalones")                       # fan upload of Track 0
    add("The Band4 - Song 1 (2004 Remaster)", "Band4")                        # remaster tag
    items.append(mk("dupvid", items[100]["snippet"]["title"], items[100]["snippet"]["videoOwnerChannelTitle"],
                    items[100]["snippet"]["resourceId"]["videoId"])); n += 1   # the same video twice
    add("Band5 - SONG 2 (Official Audio)", "Nuclear Blast Records")           # label audio, other spelling
    # look-alikes that are NOT duplicates (must stay)
    add("Band6 - Song 0 (Live at Wacken)", "Band6")
    add("Band7 - Song 0 (Acoustic)", "Band7")
    add("Band8 - Song 0 (feat. Guest)", "Band8")
    return items

TMP = tempfile.mkdtemp()
def fresh_files():
    R.MEMORY = os.path.join(TMP, 'mem.json'); R.LOG_FILE = os.path.join(TMP, 'log.txt')
    R.LINK_FILE = os.path.join(TMP, 'pl.txt'); R.DUPES = os.path.join(TMP, 'dupes.json')
    R.OVERRIDES = os.path.join(TMP, 'none.json')
    open(R.LINK_FILE, 'w').write('https://music.youtube.com/playlist?list=PLTEST\n')
    for f in (R.MEMORY, R.DUPES):
        if os.path.exists(f): os.remove(f)
    json.dump({"status": "pending", "removed": []}, open(R.DUPES, "w"))

R.time.sleep = lambda s: None
day0 = datetime.date(2026, 11, 28)
class D(datetime.date):
    cur = day0
    @classmethod
    def today(cls): return cls.cur
R.datetime.date = D

def run(yt, day, budget=180):
    D.cur = day0 + datetime.timedelta(days=day)
    R.youtube_client = lambda scheduled=False: yt
    yt.used = 0
    sys.argv = ['x', '--apply', '--scheduled', '--budget', str(budget)]
    out, buf = sys.stdout, io.StringIO()
    sys.stdout = buf
    try:
        R.main()
    except SystemExit as e:
        sys.stdout = out; print(buf.getvalue()[-3000:]); expect(False, f"day {day}: run exited ({e.code})"); return ""
    except Exception as e:
        sys.stdout = out; print(buf.getvalue()[-3000:]); expect(False, f"day {day}: run crashed ({e})"); return ""
    sys.stdout = out
    return buf.getvalue()

def songs_of(yt):
    return [R.Song(x["id"], x["snippet"]["resourceId"]["videoId"], x["snippet"]["title"],
                   x["snippet"]["videoOwnerChannelTitle"]) for x in yt.items]

# ---------------------------------------------------------------- the big playlist
random.seed(11)
fresh_files()
yt = FakeYT(build_playlist())
start_ids = [x["id"] for x in yt.items]
expect(len(start_ids) == 700, "fake playlist has 700 items")
DUPS_EXPECT = 6
log = run(yt, 0)
st = json.load(open(R.DUPES))
removed_ids = [x["videoId"] for x in st["removed"]]
expect(st["status"] == "done" and len(st["removed"]) == DUPS_EXPECT, f"cleanup removed {len(st['removed'])} (expected {DUPS_EXPECT}), status {st['status']}")
left_titles = [x["snippet"]["title"] for x in yt.items]
for must in ("Band6 - Song 0 (Live at Wacken)", "Band7 - Song 0 (Acoustic)", "Band8 - Song 0 (feat. Guest)"):
    expect(must in left_titles, f"look-alike kept: {must}")
expect("BIGBAND - Track 0 [HD]" not in left_titles and "Track 0" in left_titles, "fan upload removed, Topic copy kept")
expect("Band1 - Song 0 (Lyric Video)" not in left_titles, "lyric-video duplicate from a fan removed")
vids = [x["snippet"]["resourceId"]["videoId"] for x in yt.items]
expect(len(vids) == len(set(vids)), "the same video no longer appears twice")
expect(any(g and len(g) > 1 for g in st.get("possible_duplicates_kept", [])), "possible look-alikes listed for the owner")
expect("Rule check BEFORE" in log and "Rule check AFTER" in log, "rule check printed before and after")

# owner adds fresh songs on day 1: 10 new bands + 3 songs of one new band + 1 Bigband song
for i in range(10): yt.items.append(mk(f"N{i}", f"NewBand{i} - Fresh {i}", f"NewBand{i}"))
for i in range(3): yt.items.append(mk(f"T{i}", f"Trio - Fresh {i}", "Trio"))
yt.items.append(mk("NB", "Bigband - Brand New", "Bigband"))
total = len(yt.items)

# day 3: a hard error part-way through the moves; the run must end cleanly and the next day go on
for day in range(1, 12):
    yt.break_after = (yt.moves + 40) if day == 3 else None
    log = run(yt, day)
    if day == 3:
        expect("stopped early" in log, "error stop reported")
    s = songs_of(yt)
    if 1 <= day:
        expect(len(s) == total and len({x.id for x in s}) == total, f"day {day}: songs lost or doubled")
    if day == 1:
        expect(json.load(open(R.DUPES))["status"] == "done", "cleanup stays off")
expect(yt.deletes == DUPS_EXPECT, f"deletions happened only once ({yt.deletes})")

s = songs_of(yt)
rep = R.rule_report(s)
expect(rep["avoidable"] == 0, f"bands with room still repeat closer than {R.RULE}: {rep['worst'][:3]}")
n = len(s)
for name, c, d, cnt, m in rep["worst"]:
    if m < R.RULE:
        expect(d >= m - 3, f"crowded band {name} only {d} apart (most possible {m})")
big = [i for i, x in enumerate(s) if x.key == R.band_key("Bigband")]
expect(len(big) == 71, f"Bigband keeps all 70 songs plus its new one ({len(big)})")
pos = {x.id: i for i, x in enumerate(s)}
for i in range(10):
    expect(pos[f"itemN{i}"] < R.FRESH_TOP, f"fresh song {i} in the top {R.FRESH_TOP} (at {pos[f'itemN{i}']})")
trio = sorted(pos[f"itemT{i}"] for i in range(3))
expect(trio[0] < R.FRESH_TOP and all(b - a - 1 >= R.RULE for a, b in zip(trio, trio[1:])), f"fresh Trio spaced and near the top: {trio}")
# the seam: last songs vs first songs
seam_bad = [(k, d) for k, d, p in R.repeats(s) if p < 40 and d < R.RULE and R.max_gap(sum(1 for x in s if x.key == k), n) >= R.RULE]
expect(not seam_bad, f"seam repeats {seam_bad[:3]}")
expect("reshuffled among themselves" in log, "block reshuffle runs once the rule holds")

# ---------------------------------------------------------------- quota stop in the cleanup
random.seed(5)
fresh_files()
yt2 = FakeYT(build_playlist(), limit=3, fail_rate=0)
run(yt2, 0)
st = json.load(open(R.DUPES))
expect(st["status"] == "pending" and len(st["removed"]) == 3, f"quota stop: pending with 3 removed ({st['status']}, {len(st['removed'])})")
yt2.limit = 10 ** 9
run(yt2, 1)
st = json.load(open(R.DUPES))
expect(st["status"] == "done" and len(st["removed"]) == DUPS_EXPECT and yt2.deletes == DUPS_EXPECT,
       f"cleanup resumed and finished once ({len(st['removed'])} recorded, {yt2.deletes} deleted)")
expect(len({x["videoId"] + str(x["position"]) for x in st["removed"]}) == len(st["removed"]), "no item recorded twice")

# quota stop during moves
yt2.limit = 25
run(yt2, 2)
expect(len(yt2.items) == 700 - DUPS_EXPECT, "quota stop during moves loses nothing")

# ---------------------------------------------------------------- tiny playlists
for items in ([], [mk(1, "A - x")], [mk(1, "A - x"), mk(2, "A - y")], [mk(i, f"A - s{i}") for i in range(4)],
              [mk(i, f"B{i % 2} - s{i}") for i in range(5)]):
    fresh_files()
    y = FakeYT(list(items), fail_rate=0)
    run(y, 0)
    expect(len(y.items) == len(items), f"tiny playlist of {len(items)} unchanged in size")

print("SELF-TEST", ("FAILED: " + "; ".join(BAD)) if BAD else "PASSED")
sys.exit(1 if BAD else 0)
