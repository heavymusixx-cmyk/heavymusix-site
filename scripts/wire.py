"""HeavyMusix Metal Wire: pulls the latest worldwide metal headlines from
public RSS feeds and writes wire.js for the website. Headlines + links only
(no article text), so every story sends readers to the original source.
Runs on GitHub Actions. Python standard library only."""
import json, re, html, urllib.request, email.utils, datetime as dt
import xml.etree.ElementTree as ET

FEEDS = [
    ("Blabbermouth", "https://blabbermouth.net/feed"),
    ("Metal Injection", "https://metalinjection.net/feed"),
    ("MetalSucks", "https://www.metalsucks.net/feed/"),
    ("Decibel", "https://www.decibelmagazine.com/feed/"),
    ("Metal Hammer", "https://www.loudersound.com/feeds.xml"),
    ("Kerrang!", "https://www.kerrang.com/feed.rss"),
    ("Revolver", "https://www.revolvermag.com/feed"),
    ("Phoenix New Times", "https://www.phoenixnewtimes.com/music/feed"),
]
PER_SOURCE = 5
TOTAL = 18
AZ_WORDS = re.compile(r"metal|metalcore|deathcore|thrash|doom|hardcore|punk|death|black|grind|sludge|heavy", re.I)

def text(el, *names):
    for n in names:
        for child in el:
            tag = child.tag.split("}")[-1]
            if tag == n:
                if n == "link" and child.get("href"):
                    return child.get("href")
                if child.text:
                    return child.text.strip()
    return ""

def parse_date(s):
    if not s:
        return None
    try:
        d = email.utils.parsedate_to_datetime(s)
    except Exception:
        try:
            d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d

def clean(s):
    s = html.unescape(re.sub(r"<[^>]+>", "", s or ""))
    return re.sub(r"\s+", " ", s).strip()

def parse_feed(source, xml_bytes):
    root = ET.fromstring(xml_bytes)
    items = [e for e in root.iter() if e.tag.split("}")[-1] in ("item", "entry")]
    out = []
    for it in items:
        title = clean(text(it, "title"))
        link = text(it, "link").strip()
        when = parse_date(text(it, "pubDate", "published", "updated", "date"))
        if not title or not link.startswith("http"):
            continue
        if source == "Phoenix New Times" and not AZ_WORDS.search(title):
            continue
        out.append({"t": title, "u": link, "s": source, "d": when, "g": tag_for(title)})
    return out[:PER_SOURCE]

TAGS = [
    ("Festival", r"festival|fest\b|open air|lineup for|line-up for|wacken|hellfest|bloodstock|download fest|graspop|summer breeze|tuska|maryland deathfest|inferno|sick new world|welcome to rockville|aftershock|psycho las vegas|70000 tons"),
    ("Tour", r"\btour|tour dates|\bshows?\b|concert|headlin|support act|trek|live dates|cancel|postpone"),
    ("New music", r"album|single|\bep\b|video|new song|track|stream|release|record|announce[sd]? new|debut"),
    ("Lineup", r"join|joins|depart|leaves|left the band|quit|new (singer|vocalist|drummer|guitarist|bassist)|replace|reunit|split|disband|breakup|hiatus"),
]

def tag_for(title):
    for name, pat in TAGS:
        if re.search(pat, title, re.I):
            return name
    return "News"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (HeavyMusix Metal Wire; +https://heavymusix.com)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()

def build(all_items, now):
    cutoff = now - dt.timedelta(days=4)
    seen, keep = set(), []
    for i in all_items:
        key = re.sub(r"\W+", "", i["t"].lower())[:60]
        if key in seen or (i["d"] and i["d"] < cutoff):
            continue
        seen.add(key)
        keep.append(i)
    keep.sort(key=lambda i: i["d"] or cutoff, reverse=True)
    keep = keep[:TOTAL]
    for i in keep:
        i["d"] = (i["d"] or now).astimezone(dt.timezone(dt.timedelta(hours=-7))).strftime("%Y-%m-%d")
    return keep

RENDER = r"""
function renderWire(el,limit){
  if(!el)return;
  var w=window.WIRE||{items:[]};var items=w.items.slice(0,limit||w.items.length);
  if(!items.length){el.innerHTML='<p class="lead">Fresh headlines load here every few hours.</p>';return;}
  function esc(s){return String(s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
  function fmt(d){var p=d.split('-');var m=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];return m[+p[1]-1]+' '+(+p[2])}
  el.innerHTML='<ul class="wire">'+items.map(function(i){return '<li><span class="wtag">'+esc(i.g||'News')+'</span><a href="'+esc(i.u)+'" target="_blank" rel="noopener">'+esc(i.t)+'</a><span class="wsrc">'+esc(i.s)+' &middot; '+fmt(i.d)+'</span></li>'}).join('')+'</ul>'+
    '<p class="wupd">Updated automatically every few hours. Stories open on the original site.</p>';
}
"""

def write_js(items, updated, path="wire.js"):
    data = json.dumps({"updated": updated, "items": items}, ensure_ascii=False, indent=1)
    with open(path, "w", encoding="utf-8") as f:
        f.write("/* Auto-generated by scripts/wire.py. Do not edit by hand. */\n")
        f.write("window.WIRE=" + data + ";\n" + RENDER)

def main():
    now = dt.datetime.now(dt.timezone.utc)
    collected, ok = [], 0
    for source, url in FEEDS:
        try:
            got = parse_feed(source, fetch(url))
            collected += got
            ok += 1
            print(f"{source}: {len(got)} items")
        except Exception as e:
            print(f"{source}: skipped ({e})")
    items = build(collected, now)
    if not items:
        print("No headlines found; keeping the old wire.js")
        return
    write_js(items, now.isoformat(timespec="minutes"))
    print(f"Wrote {len(items)} headlines from {ok} feeds")

if __name__ == "__main__":
    main()
