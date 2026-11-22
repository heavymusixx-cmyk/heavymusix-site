"""Self-test for playlist_rotator.py. Runs 18 pretend days against a fake YouTube (with random
'busy' errors) and checks nothing is lost, doubled, back-to-back, or stuck. The daily workflow runs
this first; if it fails, the real playlist is never touched."""
import sys, json, os, random, datetime, types, io
import tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import playlist_rotator as R
TMP = tempfile.mkdtemp()
R.MEMORY = os.path.join(TMP, 'mem.json'); R.LOG_FILE = os.path.join(TMP, 'log.txt'); R.LINK_FILE = os.path.join(TMP, 'pl.txt')
open(R.LINK_FILE,'w').write('https://music.youtube.com/playlist?list=PLTEST\n')
if os.path.exists(R.MEMORY): os.remove(R.MEMORY)

class FakeYT:
    """Mimics the YouTube Data API calls the rotator makes, incl. random busy errors."""
    def __init__(self, n):
        self.items = [self.mk(i, f"Band{i%60} - Song{i}") for i in range(n)]
        self.moves = 0; self.fail_rate = 0.05
    def mk(self, i, title):
        return {"id": f"item{i}", "snippet": {"title": title, "videoOwnerChannelTitle": "", "resourceId": {"kind":"youtube#video","videoId": f"v{i}"}}}
    def channels(self): return types.SimpleNamespace(list=lambda **k: types.SimpleNamespace(execute=lambda: {"items":[{"id":"me","snippet":{"title":"HeavyMusix"}}]}))
    def playlists(self): return types.SimpleNamespace(list=lambda **k: types.SimpleNamespace(execute=lambda: {"items":[{"snippet":{"channelTitle":"HeavyMusix","channelId":"me"}}]}))
    def playlistItems(self):
        yt = self
        def lst(part, playlistId, maxResults, pageToken=None):
            st = int(pageToken or 0)
            r = {"items": yt.items[st:st+maxResults]}
            if st+maxResults < len(yt.items): r["nextPageToken"] = str(st+maxResults)
            return types.SimpleNamespace(execute=lambda: r)
        def upd(part, body):
            def ex():
                if random.random() < yt.fail_rate: raise Exception("HttpError 503 SERVICE_UNAVAILABLE")
                i = next(k for k,x in enumerate(yt.items) if x["id"]==body["id"])
                it = yt.items.pop(i); yt.items.insert(body["snippet"]["position"], it); yt.moves += 1
            return types.SimpleNamespace(execute=ex)
        return types.SimpleNamespace(list=lst, update=upd)

random.seed(7)
yt = FakeYT(690)
R.youtube_client = lambda scheduled=False: yt
R.time.sleep = lambda s: None
day0 = datetime.date(2026,11,22)
class D(datetime.date):
    cur = day0
    @classmethod
    def today(cls): return cls.cur
R.datetime.date = D

RESULTS = []
d_index = lambda day: (day - day0).days
def run(day, label):
    D.cur = day
    sys.argv = ['x','--apply','--scheduled']
    before = yt.moves
    out = sys.stdout
    sys.stdout = io.StringIO()
    try:
        R.main()
    except SystemExit as e:
        sys.stdout = out; print(label, "EXITED", e.code); sys.exit(1)
    sys.stdout = out
    fresh_pos = [i for i,x in enumerate(yt.items) if x["id"].startswith("itemN")]
    mem = json.load(open(R.MEMORY))["PLTEST"]
    RESULTS.append((d_index(day), fresh_pos, len(mem['dealt'])))
    print(f"{label} {day}: moves {yt.moves-before}, fresh positions {fresh_pos[:15]}{'...' if len(fresh_pos)>15 else ''}, dealt {len(mem['dealt'])}, added {len(mem.get('added',{}))}")

run(day0, "day 1 (first run)")
# owner adds 12 Keep songs
for i in range(12): yt.items.append(yt.mk(f"N{i}", f"NewBand{i%4} - Fresh{i}"))
for d in range(1, 18):
    run(day0 + datetime.timedelta(days=d), f"day {d+1}")
# checks
keys = [R.guess_artist(x["snippet"]["title"], "")[0] for x in yt.items]
bad = []
if any(keys[i] == keys[i-1] for i in range(1, len(keys))): bad.append("same band back-to-back")
if len(yt.items) != 702 or len({x["id"] for x in yt.items}) != 702: bad.append("songs lost or doubled")
for day, pos, dealt in RESULTS:
    if 1 <= day <= 14 and (len(pos) != 12 or max(pos) >= R.FRESH_TOP): bad.append(f"day {day+1}: fresh songs not all in the top {R.FRESH_TOP}")
if RESULTS[-1][1] and max(RESULTS[-1][1]) < R.FRESH_TOP: bad.append("fresh songs never released after 2 weeks")
if not any(d < p for (_, _, p), (_, _, d) in zip(RESULTS, RESULTS[1:])): bad.append("the pass never wrapped to a fresh shuffle")
print("SELF-TEST", "FAILED: " + "; ".join(bad) if bad else "PASSED")
sys.exit(1 if bad else 0)
