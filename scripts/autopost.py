"""HeavyMusix auto-poster: posts to HeavyMusix's OWN accounts only (Threads, Instagram, Facebook Page).
Never posts in groups or other people's spaces. Runs on GitHub twice a day.

Morning slot (8:41 AM Arizona): today's lead story.   Evening slot (5:41 PM): today in metal history.
Text comes from social/queue.json (written by the morning content task) when it has an entry for today and the slot;
otherwise it is built from news.js / history.js. Each platform is skipped quietly until its secrets exist:
  THREADS_TOKEN (+ THREADS_USER_ID, optional) (Threads API)
  IG_USER_ID + META_PAGE_TOKEN             (Instagram professional account linked to the Facebook Page)
  FB_PAGE_ID + META_PAGE_TOKEN             (Facebook Page)
Never posts the same thing twice: social/posted.json remembers what went out."""
import datetime, json, os, re, subprocess, sys, time, urllib.parse, urllib.request

SITE = "https://heavymusix.com/"
AZ = datetime.timezone(datetime.timedelta(hours=-7))
now = datetime.datetime.now(AZ)
today = now.date().isoformat()
slot = sys.argv[1] if len(sys.argv) > 1 else ("morning" if now.hour < 13 else "evening")


def js(file, var):
    code = f"eval(require('fs').readFileSync({json.dumps(file)},'utf8')+';process.stdout.write(JSON.stringify({var}))')"
    return json.loads(subprocess.check_output(["node", "-e", code], text=True))


def slug_of(n):
    return n["date"] + "-" + re.sub(r"[^a-z0-9]+", "-", n["title"].lower()).strip("-")[:60]


def clip(s, n):
    return s if len(s) <= n else s[:n - 1].rsplit(" ", 1)[0] + "…"


def load(path, default):
    try:
        return json.load(open(path, encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return default


# ---------- what to post
queue = load("social/queue.json", [])
item = next((q for q in queue if q.get("date") == today and q.get("slot") == slot), None)
if not item:
    if slot == "morning":
        news = [n for n in js("news.js", "NEWS") if n["date"] == today and n.get("tag") not in ("Site", "Coming soon")]
        if not news:
            print("No story for today yet; nothing to post."); sys.exit(0)
        n, s = news[0], slug_of(news[0])
        item = {"text": f"{n['title']}\n\n{clip(n['text'][0], 330)}",
                "link": f"{SITE}news/{s}.html", "image": f"{SITE}og/{s}.png",
                "tags": "#HeavyMusixRadio #UnsignedMetal #MetalNews"}
    else:
        hist = js("history.js", "HISTORY").get(now.strftime("%m-%d"), [])
        if not hist:
            print("No history for today; nothing to post."); sys.exit(0)
        h = sorted(hist, key=lambda x: x["year"])[0]
        item = {"text": f"Today in metal history: {h['year']}\n\n{clip(h['text'], 330)}\n\nWhat else happened today?",
                "link": f"{SITE}today/", "image": f"{SITE}og/history-{now.strftime('%m-%d')}.png",
                "tags": "#MetalHistory #HeavyMusixRadio"}
key = f"{today}-{slot}"
posted = load("social/posted.json", {})
done = posted.get(key, {})


def call(url, data):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(), method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def permalink(url):
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read()).get("permalink", "")
    except Exception:
        return ""


def image_ok(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, method="HEAD"), timeout=30) as r:
            return r.status == 200
    except Exception:
        return False


img = item.get("image") if item.get("image") and image_ok(item["image"]) else None
results = {}

# ---------- Threads (500 characters max)
if os.getenv("THREADS_TOKEN") and "threads" not in done:
    text = clip(item["text"], 500 - len(item["link"]) - 4) + "\n\n" + item["link"]
    tok = os.environ["THREADS_TOKEN"]
    try:
        uid = os.getenv("THREADS_USER_ID")
        if not uid:   # only the token was added: look up the account id from it
            with urllib.request.urlopen(f"https://graph.threads.net/v1.0/me?fields=id,username&access_token={tok}", timeout=30) as r:
                uid = json.loads(r.read())["id"]
        base = f"https://graph.threads.net/v1.0/{uid}"
        c = call(f"{base}/threads", {"media_type": "IMAGE" if img else "TEXT", "text": text, **({"image_url": img} if img else {}), "access_token": tok})
        time.sleep(30)
        p = call(f"{base}/threads_publish", {"creation_id": c["id"], "access_token": tok})
        results["threads"] = permalink(f"https://graph.threads.net/v1.0/{p['id']}?fields=permalink&access_token={tok}") or p.get("id", "ok")
    except Exception as e:
        results["threads_error"] = str(e)[:300]

# ---------- Instagram (needs a picture)
if os.getenv("META_PAGE_TOKEN") and os.getenv("IG_USER_ID") and img and "instagram" not in done:
    cap = f"{item['text']}\n\nFull story: link in bio or heavymusix.com\n\n{item.get('tags', '#HeavyMusixRadio')}"
    base = f"https://graph.facebook.com/v21.0/{os.environ['IG_USER_ID']}"
    tok = os.environ["META_PAGE_TOKEN"]
    try:
        c = call(f"{base}/media", {"image_url": img, "caption": clip(cap, 2100), "access_token": tok})
        time.sleep(30)
        p = call(f"{base}/media_publish", {"creation_id": c["id"], "access_token": tok})
        results["instagram"] = permalink(f"https://graph.facebook.com/v21.0/{p['id']}?fields=permalink&access_token={tok}") or p.get("id", "ok")
    except Exception as e:
        results["instagram_error"] = str(e)[:300]

# ---------- Facebook Page
if os.getenv("META_PAGE_TOKEN") and os.getenv("FB_PAGE_ID") and "facebook" not in done:
    try:
        p = call(f"https://graph.facebook.com/v21.0/{os.environ['FB_PAGE_ID']}/feed",
                 {"message": item["text"], "link": item["link"], "access_token": os.environ["META_PAGE_TOKEN"]})
        results["facebook"] = f"https://www.facebook.com/{p['id']}" if p.get("id") else "ok"
    except Exception as e:
        results["facebook_error"] = str(e)[:300]

def call_json(url, data, headers=None, raw=None, ctype="application/json"):
    body = raw if raw is not None else json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": ctype, "User-Agent": "HeavyMusix-autopost", **(headers or {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        txt = r.read()
        return json.loads(txt) if txt else {}


title = item["text"].split("\n")[0]
blurb = item["text"].split("\n\n", 1)[1] if "\n\n" in item["text"] else ""

# ---------- Bluesky (300 characters max; link card with the share picture)
if os.getenv("BLUESKY_HANDLE") and os.getenv("BLUESKY_APP_PASSWORD") and "bluesky" not in done:
    try:
        api = "https://bsky.social/xrpc/"
        ses = call_json(api + "com.atproto.server.createSession",
                        {"identifier": os.environ["BLUESKY_HANDLE"], "password": os.environ["BLUESKY_APP_PASSWORD"]})
        auth = {"Authorization": "Bearer " + ses["accessJwt"]}
        tags = " ".join(t for t in item.get("tags", "").split() if t.startswith("#"))[:60]
        text = clip(item["text"], 300 - len(tags) - 2) + ("\n\n" + tags if tags else "")
        card = {"uri": item["link"], "title": clip(title, 300), "description": clip(blurb, 300)}
        if img:
            try:
                with urllib.request.urlopen(img, timeout=30) as r:
                    data = r.read()
                if len(data) < 950000:
                    card["thumb"] = call_json(api + "com.atproto.repo.uploadBlob", None, auth, raw=data, ctype="image/png")["blob"]
            except Exception:
                pass
        facets, b = [], text.encode("utf-8")
        for t in tags.split():   # make the hashtags real tags
            i = b.find(t.encode("utf-8"))
            if i >= 0:
                facets.append({"index": {"byteStart": i, "byteEnd": i + len(t.encode("utf-8"))},
                               "features": [{"$type": "app.bsky.richtext.facet#tag", "tag": t[1:]}]})
        rec = {"$type": "app.bsky.feed.post", "text": text, "createdAt": now.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
               "embed": {"$type": "app.bsky.embed.external", "external": card}, "langs": ["en"]}
        if facets:
            rec["facets"] = facets
        r = call_json(api + "com.atproto.repo.createRecord", {"repo": ses["did"], "collection": "app.bsky.feed.post", "record": rec}, auth)
        results["bluesky"] = f"https://bsky.app/profile/{ses.get('handle', os.environ['BLUESKY_HANDLE'])}/post/{r['uri'].rsplit('/', 1)[-1]}"
    except Exception as e:
        results["bluesky_error"] = str(e)[:300]

# ---------- Discord (HeavyMusix's own server, through a channel webhook)
if os.getenv("DISCORD_WEBHOOK_URL") and "discord" not in done:
    try:
        emb = {"title": clip(title, 250), "url": item["link"], "description": clip(blurb, 1000), "color": 0xA3121B,
               "footer": {"text": "HeavyMusix: Where every MetalHead and Band belongs"}}
        if img:
            emb["image"] = {"url": img}
        m = call_json(os.environ["DISCORD_WEBHOOK_URL"] + "?wait=true",
                      {"username": "HeavyMusix", "content": "", "embeds": [emb], "allowed_mentions": {"parse": []}})
        gid = os.getenv("DISCORD_SERVER_ID", "")
        results["discord"] = f"https://discord.com/channels/{gid}/{m['channel_id']}/{m['id']}" if gid else f"message {m.get('id', 'ok')}"
    except Exception as e:
        results["discord_error"] = str(e)[:300]

if not results:
    print("No accounts connected yet (or already posted). Nothing to do."); sys.exit(0)
done.update({k: v for k, v in results.items() if not k.endswith("_error")})
done["what"] = item["text"].split("\n")[0][:120]
done["site_link"] = item["link"]
posted[key] = done
cutoff = (now.date() - datetime.timedelta(days=60)).isoformat()
posted = {k: v for k, v in posted.items() if k[:10] >= cutoff}
os.makedirs("social", exist_ok=True)
json.dump(posted, open("social/posted.json", "w"), indent=1)
print(json.dumps(results, indent=1))
sys.exit(1 if any(k.endswith("_error") for k in results) else 0)
