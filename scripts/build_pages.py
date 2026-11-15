"""HeavyMusix page builder. Runs on GitHub after every news update and every few hours.

Builds real, search-friendly pages from the site's data files:
  news/<story>.html      one page per news story (from news.js), with Google News labels
  bands/<band>.html      one page per band on the radio (from show/bands.json + show/catalog.json)
  episodes/<n>.html      one page per live Radio Show episode (from show/episodes.json)
  arizona-metal-shows.html   Phoenix / Arizona metal shows this week and coming up (from shows.js)
  feed.xml               RSS news feed (latest stories)
  sitemap.xml            every page, for Google and Bing

Never edit the generated files by hand; edit news.js, shows.js or show/*.json instead.
"""
import datetime, html, json, os, re, shutil, subprocess
from email.utils import format_datetime
from urllib.parse import quote

SITE = "https://heavymusix.com/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
AZ = datetime.timezone(datetime.timedelta(hours=-7))          # Arizona, no daylight saving
TODAY = datetime.datetime.now(AZ).date()
esc = lambda s: html.escape(str(s or ""), quote=True)


def js_data(file, var):
    """Read a JavaScript data file (news.js / shows.js) with node and return the array."""
    code = (f"eval(require('fs').readFileSync({json.dumps(file)},'utf8')"
            f"+';process.stdout.write(JSON.stringify({var}))')")
    return json.loads(subprocess.check_output(["node", "-e", code], text=True))


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return default


def slug_of(n):  # same as slugOf() in news.js
    return n["date"] + "-" + re.sub(r"[^a-z0-9]+", "-", n["title"].lower()).strip("-")[:60]


def fmt_date(d):
    y, m, dd = map(int, d.split("-"))
    return datetime.date(y, m, dd).strftime("%B %-d, %Y")


# ---------------------------------------------------------------- page shell
TEMPLATE = open("article.html", encoding="utf-8").read()
HEADER = re.search(r"<body>(.*?</header>)", TEMPLATE, re.S).group(1)
FOOTER = re.search(r"(<footer.*?</footer>)", TEMPLATE, re.S).group(1)
STYLE = re.search(r'<link rel="stylesheet" href="([^"]+)"', TEMPLATE).group(1)
RADIO = re.search(r'<script src="(radio\.js[^"]*)"', TEMPLATE).group(1)


def page(path, title, desc, body, nav=None, ld=None, extra_head=""):
    head_nav = HEADER.replace(' class="on"', "")
    if nav:
        head_nav = head_nav.replace(f'<a href="{nav}">', f'<a href="{nav}" class="on">', 1)
    ld_tag = (f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>\n'
              if ld else "")
    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<base href="/">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{SITE}{path}">
<meta property="og:type" content="{'article' if path.startswith('news/') else 'website'}">
<meta property="og:site_name" content="HeavyMusix">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{SITE}{path}">
<meta name="twitter:card" content="summary">
<link rel="alternate" type="application/rss+xml" title="HeavyMusix metal news" href="{SITE}feed.xml">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Pirata+One&family=Archivo:wdth,wght@62..125,400..800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{STYLE}">
{extra_head}{ld_tag}</head>
<body>
<!-- Built automatically by scripts/build_pages.py. Do not edit by hand. -->
{head_nav}

{body}

{FOOTER}
<script src="hmx.js?v=2"></script>
<script src="{RADIO}"></script>
</body>
</html>
"""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)


ORG = {"@type": "Organization", "name": "HeavyMusix", "url": SITE}
pages = []   # (path, lastmod) for the sitemap


def fresh_dir(d):
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)


# ---------------------------------------------------------------- news stories
news = js_data("news.js", "NEWS")
fresh_dir("news")
for i, n in enumerate(news):
    slug = slug_of(n)
    paras = "".join(f'<p class="src">{esc(p)}</p>' if re.match(r"(?i)source:", p) else f"<p>{esc(p)}</p>"
                    for p in n["text"])
    more = [m for m in news if m is not n][:6]
    body = f"""<section><div class="wrap">
    <article class="post story">
      <span class="tag">{esc(n['tag'])}</span>
      <div class="date muted"><time datetime="{n['date']}">{fmt_date(n['date'])}</time> &middot; HeavyMusix</div>
      <h1>{esc(n['title'])}</h1>
      {paras}
    </article>
    <h2 class="sub">More metal news</h2>
    <ul class="morenews">{''.join(f'<li><a href="news/{slug_of(m)}.html">{esc(m["title"])}</a><span class="wsrc">{fmt_date(m["date"])}</span></li>' for m in more)}</ul>
    <div class="btns"><a class="btn ghost" href="news.html">All news</a> <a class="btn ghost" href="feed.xml">News feed (RSS)</a></div>
</div></section>"""
    desc = n["text"][0][:155]
    ld = {"@context": "https://schema.org", "@type": "NewsArticle", "headline": n["title"][:110],
          "datePublished": n["date"] + "T05:00:00-07:00", "dateModified": n["date"] + "T05:00:00-07:00",
          "articleSection": n["tag"], "description": desc,
          "author": ORG, "publisher": ORG,
          "mainEntityOfPage": f"{SITE}news/{slug}.html"}
    page(f"news/{slug}.html", f"{n['title']} | HeavyMusix", desc, body, nav="news.html", ld=ld)
    pages.append((f"news/{slug}.html", n["date"]))

# ---------------------------------------------------------------- RSS feed
items = []
for n in news[:40]:
    y, m, d = map(int, n["date"].split("-"))
    when = format_datetime(datetime.datetime(y, m, d, 5, 0, tzinfo=AZ))
    url = f"{SITE}news/{slug_of(n)}.html"
    text = " ".join(p for p in n["text"] if not re.match(r"(?i)source:", p))
    items.append(f"""  <item>
    <title>{esc(n['title'])}</title>
    <link>{url}</link>
    <guid isPermaLink="true">{url}</guid>
    <pubDate>{when}</pubDate>
    <category>{esc(n['tag'])}</category>
    <description>{esc(text)}</description>
  </item>""")
with open("feed.xml", "w", encoding="utf-8") as f:
    f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>HeavyMusix: metal news from around the world</title>
  <link>{SITE}news.html</link>
  <atom:link href="{SITE}feed.xml" rel="self" type="application/rss+xml"/>
  <description>Metal news written by HeavyMusix: new albums, tours, festivals, the underground and Arizona metal.</description>
  <language>en-us</language>
  <lastBuildDate>{format_datetime(datetime.datetime.now(AZ))}</lastBuildDate>
{chr(10).join(items)}
</channel>
</rss>
""")

# ---------------------------------------------------------------- bands
bands = load_json("show/bands.json", {})
catalog = load_json("show/catalog.json", [])
eps = load_json("show/episodes.json", {}).get("episodes", [])
live = [e for e in eps if e.get("status") == "live"]
where = lambda b: ", ".join(x for x in (b.get("city"), b.get("region"), b.get("country")) if x)
fresh_dir("bands")
for key, b in bands.items():
    songs = [s for s in catalog if s.get("b") == key]
    if not songs:
        continue
    loc, genre = where(b), b.get("genre", "")
    bits = [x for x in (genre, loc) if x]
    intro = b.get("bio") or (f"{b['name']} is a {genre.lower() if genre else 'metal'} band"
                             + (f" from {loc}" if loc else "")
                             + f". HeavyMusix Radio plays {len(songs)} of their song{'s' if len(songs) != 1 else ''}.")
    links = {k: v for k, v in (b.get("links") or {}).items() if v}
    link_html = "".join(f'<a class="btn ghost" href="{esc(v)}">{esc("Band merch" if k == "merch" else k.capitalize())}</a>'
                        for k, v in links.items())
    on_eps = [e for e in live if any(s.get("b") == key for s in e.get("songs", []))]
    song_list = "".join(
        f'<li><button type="button" class="playbtn" data-v="{esc(s["v"])}" data-label="{esc(b["name"] + " – " + s["t"])}" '
        f'aria-label="Play {esc(b["name"] + " – " + s["t"])}">&#9654; Play</button>'
        f'<span class="sinfo"><strong>{esc(s["t"])}</strong></span></li>' for s in songs)
    body = f"""<section class="hero"><div class="wrap">
  <p class="kicker">{'HeavyMusix unsigned pick' if b.get('unsigned') else 'On HeavyMusix Radio'}</p>
  <h1>{esc(b['name'])}</h1>
  <p class="lead">{esc(' · '.join(bits))}</p>
  <p>{esc(intro)}</p>
  {f'<div class="btns">{link_html}</div>' if link_html else ''}
  <h2 class="sub">{len(songs)} song{'s' if len(songs) != 1 else ''} on HeavyMusix Radio</h2>
  <ul class="songs">{song_list}</ul>
  {('<p class="wupd">Played on ' + ', '.join(f'<a href="episodes/{e["n"]}.html">Show #{e["n"]}</a>' for e in on_eps) + '.</p>') if on_eps else ''}
  <div class="btns"><a class="btn ghost" href="bands.html">Find another band</a></div>
</div></section>"""
    desc = (f"{b['name']}: {genre} from {loc}. Listen to {len(songs)} song{'s' if len(songs) != 1 else ''} free on HeavyMusix Radio."
            if loc else f"{b['name']} on HeavyMusix Radio: listen to {len(songs)} songs free.")
    ld = {"@context": "https://schema.org", "@type": "MusicGroup", "name": b["name"], "url": f"{SITE}bands/{key}.html"}
    if genre: ld["genre"] = genre
    if loc: ld["foundingLocation"] = {"@type": "Place", "name": loc}
    page(f"bands/{key}.html", f"{b['name']} | {genre or 'Metal'}{' from ' + (b.get('city') or b.get('country')) if (b.get('city') or b.get('country')) else ''} | HeavyMusix",
         desc[:160], body, nav="bands.html", ld=ld)
    pages.append((f"bands/{key}.html", TODAY.isoformat()))

# ---------------------------------------------------------------- radio show episodes
fresh_dir("episodes")
for e in live:
    tracks = "".join(f'<li><a href="bands/{esc(s["b"])}.html">{esc(s["band"])}</a> &ndash; {esc(s["song"])}</li>'
                     for s in e.get("songs", []))
    body = f"""<section class="hero"><div class="wrap">
  <p class="kicker">HeavyMusix Radio Show{(' &middot; ' + esc(e['live'])) if e.get('live') else ''}</p>
  <h1>{esc(e['title'])}</h1>
  <p class="lead">An hour of unsigned and heavy-hitting metal from around the world, hosted by Heavy.</p>
  <button type="button" class="btn playep" data-n="{e['n']}">&#9654; Play Show #{e['n']}</button>
  <h2 class="sub">Track list</h2>
  <ol class="tracks">{tracks}</ol>
  <div class="btns"><a class="btn ghost" href="show.html">All episodes</a></div>
</div></section>"""
    names = ", ".join(dict.fromkeys(s["band"] for s in e.get("songs", [])))
    page(f"episodes/{e['n']}.html", f"{e['title']} | HeavyMusix Radio",
         f"{e['title']}: {names}"[:160], body, nav="show.html")
    pages.append((f"episodes/{e['n']}.html", (e.get("live") or TODAY.isoformat())[:10]))

# ---------------------------------------------------------------- Arizona shows this week
shows = sorted((s for s in js_data("shows.js", "SHOWS") if s["date"] >= TODAY.isoformat()),
               key=lambda s: (s["date"], s["city"]))
week_end = (TODAY + datetime.timedelta(days=7)).isoformat()
this_week = [s for s in shows if s["date"] < week_end]
later = [s for s in shows if s["date"] >= week_end][:60]


def show_rows(lst):
    if not lst:
        return '<p class="muted">No metal shows on the calendar yet. Check back soon.</p>'
    return '<ul class="morenews">' + "".join(
        f'<li><strong>{esc(s["bands"])}</strong><span class="wsrc">'
        f'{datetime.date.fromisoformat(s["date"]).strftime("%a, %b %-d")} &middot; {esc(s["venue"])}, {esc(s["city"])}</span></li>'
        for s in lst) + "</ul>"


cities = sorted({s["city"] for s in shows})
body = f"""<section class="hero"><div class="wrap">
  <p class="kicker">Arizona metal</p>
  <h1>Metal shows in Phoenix and Arizona this week</h1>
  <p class="lead">Every heavy show we know about in Phoenix, Tempe, Mesa, Tucson and around Arizona. Updated every day. Week of {TODAY.strftime('%B %-d, %Y')}.</p>
  <h2 class="sub">This week</h2>
  {show_rows(this_week)}
  <h2 class="sub">Coming up</h2>
  {show_rows(later)}
  <p class="wupd">Playing a show in Arizona? Send the details to info@heavymusix.com.</p>
  <div class="btns"><a class="btn ghost" href="arizona.html">Arizona metal news</a></div>
</div></section>"""
events = [{"@context": "https://schema.org", "@type": "MusicEvent", "name": s["bands"],
           "startDate": s["date"],
           "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
           "eventStatus": "https://schema.org/EventScheduled",
           "location": {"@type": "Place", "name": s["venue"],
                        "address": {"@type": "PostalAddress", "addressLocality": s["city"],
                                    "addressRegion": "AZ", "addressCountry": "US"}},
           "performer": [{"@type": "MusicGroup", "name": p.strip()} for p in s["bands"].split(",") if p.strip()]}
          for s in shows[:40]]
page("arizona-metal-shows.html", "Metal shows in Phoenix & Arizona this week | HeavyMusix",
     f"Metal concerts in Phoenix, Tempe, Mesa, Tucson and across Arizona this week and coming up. Updated daily. {len(shows)} shows listed.",
     body, nav="arizona.html", ld=events or None)
pages.append(("arizona-metal-shows.html", TODAY.isoformat()))

# ---------------------------------------------------------------- sitemap
MAIN = ["", "news.html", "show.html", "bands.html", "arizona.html", "series.html",
        "submit.html", "shop.html", "about.html", "checklist-ep1.html"]
urls = [(p, TODAY.isoformat()) for p in MAIN] + pages
with open("sitemap.xml", "w", encoding="utf-8") as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
    for p, d in urls:
        f.write(f"  <url><loc>{esc(SITE + quote(p))}</loc><lastmod>{d}</lastmod></url>\n")
    f.write("</urlset>\n")

print(f"Built {len(news)} stories, {sum(1 for p, _ in pages if p.startswith('bands/'))} band pages, "
      f"{len(live)} episodes, {len(shows)} Arizona shows; feed.xml and sitemap.xml ({len(urls)} pages).")
