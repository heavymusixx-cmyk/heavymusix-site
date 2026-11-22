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

def cut(s, n):
    """Shorten to n chars at a word boundary, with an ellipsis (no cut-off words)."""
    s = " ".join(str(s).split())
    if len(s) <= n:
        return s
    s = s[:n - 1].rsplit(" ", 1)[0].rstrip(" ,;:-")
    return s + "…"


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


def page(path, title, desc, body, nav=None, ld=None, extra_head="", image="og/default.png"):
    head_nav = HEADER.replace(' class="on" aria-current="page"', "").replace(' class="on"', "")
    if nav:
        head_nav = head_nav.replace(f'<a href="{nav}">', f'<a href="{nav}" class="on" aria-current="page">', 1)
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
<meta property="og:image" content="{SITE}{image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="alternate" type="application/rss+xml" title="HeavyMusix metal news" href="{SITE}feed.xml">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="images/app/apple-touch-icon.png">
<meta name="theme-color" content="#0a0a0a">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Creepster&family=Metal+Mania&family=New+Rocker&family=Nosifer&family=Pirata+One&family=UnifrakturCook:wght@700&family=Archivo:wdth,wght@62..125,400..800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{STYLE}">
<script src="skin.js?v=5"></script>
{extra_head}{ld_tag}</head>
<body>
<!-- Built automatically by scripts/build_pages.py. Do not edit by hand. -->
{head_nav}
<main id="main">
{body}
</main>
{FOOTER}
<script src="hmx.js?v=5"></script>
<script src="{RADIO}"></script>
<script data-goatcounter="https://heavymusix.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
</body>
</html>
"""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)


ORG = {"@type": "Organization", "name": "HeavyMusix", "url": SITE,
       "logo": {"@type": "ImageObject", "url": SITE + "og/default.png"},
       "sameAs": ["https://www.instagram.com/heavymusixradio/", "https://www.threads.net/@heavymusixradio",
                  "https://www.youtube.com/@HeavyMusix"]}
HEAVY = {"@type": "Person", "name": "Heavy", "url": SITE + "about.html", "jobTitle": "Editor and DJ, HeavyMusix"}


def crumbs(*items):
    """Breadcrumb trail for Google: crumbs(("News", "news.html"), ("Story title", "news/x.html"))."""
    trail = [("Home", "")] + list(items)
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + u}
                                for i, (n, u) in enumerate(trail)]}
pages = []   # (path, lastmod) for the sitemap


def fresh_dir(d):
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)


# ---------------------------------------------------------------- share pictures (1200x630, for Instagram/Facebook/Threads link previews)
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None
FONT = os.path.join("assets", "fonts", "DejaVuSans-Bold.ttf")


def share_picture(path, headline, footer, force=False):
    if Image is None or (os.path.exists(path) and not force):
        return
    W, H = 1200, 630
    im = Image.new("RGB", (W, H), (8, 8, 8))
    d = ImageDraw.Draw(im)
    for i in range(H):  # red glow from the top right
        d.line([(0, i), (W, i)], fill=(int(8 + 90 * max(0, 1 - i / 420)), 8, 10))
    d.rectangle([0, 0, W, 86], fill=(163, 18, 27))
    d.text((48, 18), "HEAVYMUSIX", font=ImageFont.truetype(FONT, 46), fill=(244, 236, 220))
    d.text((W - 48, 30), "Every band gets a turn.", font=ImageFont.truetype(FONT, 26), fill=(244, 236, 220), anchor="ra")
    size = 64
    while size > 34:
        f = ImageFont.truetype(FONT, size)
        words, lines, cur = headline.split(), [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if d.textlength(t, font=f) <= W - 96:
                cur = t
            else:
                lines.append(cur); cur = w
        lines.append(cur)
        if len(lines) * size * 1.18 <= 400:
            break
        size -= 4
    y = 120 + (400 - len(lines) * size * 1.18) / 2
    for ln in lines:
        d.text((48, y), ln, font=f, fill=(244, 236, 220))
        y += size * 1.18
    d.rectangle([48, H - 78, 160, H - 72], fill=(209, 22, 31))
    d.text((48, H - 60), footer, font=ImageFont.truetype(FONT, 26), fill=(190, 180, 170))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, optimize=True)


share_picture("og/default.png", "Unsigned metal from around the world + the heavy hitters you love",
              "heavymusix.com  ·  HeavyMusix Radio, news, bands", force=not os.path.exists("og/default.png"))

# ---------------------------------------------------------------- which bands a story mentions
bands = load_json("show/bands.json", {})
_names = sorted(((b["name"], k) for k, b in bands.items() if b.get("songs") and len(b.get("name", "")) >= 3),
                key=lambda x: -len(x[0]))


COMMON_WORDS = {"Down", "Death", "Riot", "Kingdom", "Opeth Down"}   # band names that are also everyday words


def bands_in(text, title=""):
    found, taken = [], []
    for name, key in _names:
        if name in COMMON_WORDS and not re.search(r"(?<![\w])" + re.escape(name) + r"(?![\w])", title):
            continue  # only link these when the headline names them
        for m in re.finditer(r"(?<![\w])" + re.escape(name) + r"(?![\w])", text):
            if any(a <= m.start() < b for a, b in taken):
                continue
            taken.append((m.start(), m.end()))
            if key not in found:
                found.append(key)
    return found


story_bands = {}

# ---------------------------------------------------------------- news stories
news = js_data("news.js", "NEWS")
fresh_dir("news")
for i, n in enumerate(news):
    slug = slug_of(n)
    paras = "".join(f'<p class="src">{esc(p)}</p>' if re.match(r"(?i)source:", p) else f"<p>{esc(p)}</p>"
                    for p in n["text"])
    more = [m for m in news if m is not n][:6]
    in_story = bands_in(n["title"] + " " + " ".join(n["text"]), n["title"])
    for k in in_story:
        story_bands.setdefault(k, []).append(n)
    chips = ("<h2 class=\"sub\">Bands in this story</h2><ul class=\"bandchips\">" +
             "".join(f'<li><a href="bands/{esc(k)}.html">&#9654; {esc(bands[k]["name"])} on HeavyMusix Radio</a></li>' for k in in_story) +
             "</ul>") if in_story else ""
    share_picture(f"og/{slug}.png", n["title"], f"heavymusix.com  ·  {n['tag']}  ·  {fmt_date(n['date'])}")
    body = f"""<section><div class="wrap">
    <article class="post story">
      <span class="tag">{esc(n['tag'])}</span>
      <div class="date muted"><time datetime="{n['date']}">{fmt_date(n['date'])}</time> &middot; By <a href="about.html#heavy">Heavy</a> &middot; <a href="about.html#news-standards">How we write the news</a></div>
      <h1>{esc(n['title'])}</h1>
      {paras}
      <div class="sharebar"><button type="button" class="sharebtn" data-share>Share this story</button><a class="sharebtn" href="https://www.instagram.com/heavymusixradio/">Follow @heavymusixradio</a></div>
      {chips}
    </article>
    <h2 class="sub">More metal news</h2>
    <ul class="morenews">{''.join(f'<li><a href="news/{slug_of(m)}.html">{esc(m["title"])}</a><span class="wsrc">{fmt_date(m["date"])}</span></li>' for m in more)}</ul>
    <div class="btns"><a class="btn ghost" href="news.html">All news</a> <a class="btn ghost" href="feed.xml" target="_blank" rel="noopener">News feed (RSS)</a></div>
</div></section>"""
    desc = cut(n["text"][0], 155)
    ld = {"@context": "https://schema.org", "@type": "NewsArticle", "headline": cut(n["title"], 110),
          "datePublished": n["date"] + "T05:00:00-07:00", "dateModified": n["date"] + "T05:00:00-07:00",
          "articleSection": n["tag"], "description": desc,
          "author": HEAVY, "publisher": ORG, "isAccessibleForFree": True,
          "mainEntityOfPage": f"{SITE}news/{slug}.html"}
    ld["image"] = f"{SITE}og/{slug}.png"
    page(f"news/{slug}.html", f"{n['title']} | HeavyMusix", desc, body, nav="news.html",
         ld=[ld, crumbs(("News", "news.html"), (n["title"][:80], f"news/{slug}.html"))], image=f"og/{slug}.png")
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
# No genre labels anywhere on the site (owner, Nov 21, 2026): it's metal, period.

catalog = load_json("show/catalog.json", [])
UNPLAYABLE = {x["v"] for x in load_json("show/unplayable.json", {"songs": []}).get("songs", [])}


def play_button(v, label):
    """Play button, or a YouTube link for songs whose owners only allow them on YouTube."""
    if v in UNPLAYABLE:
        return (f'<a class="playbtn yt" href="https://www.youtube.com/watch?v={esc(v)}" target="_blank" rel="noopener" '
                f'aria-label="{esc(label)} (plays on YouTube, opens a new tab)">&#9654; YouTube &#8599;</a>')
    return (f'<button type="button" class="playbtn" data-v="{esc(v)}" data-label="{esc(label)}" '
            f'aria-label="Play {esc(label)}">&#9654; Play</button>')
eps = load_json("show/episodes.json", {}).get("episodes", [])
live = [e for e in eps if e.get("status") == "live"]
where = lambda b: ", ".join(x for x in (b.get("city"), b.get("region"), b.get("country")) if x)
fresh_dir("bands")
for key, b in bands.items():
    songs = [s for s in catalog if s.get("b") == key]
    if not songs:
        continue
    loc = where(b)
    bits = [x for x in (loc,) if x]
    intro = b.get("bio") or (f"{b['name']} is a metal band"
                             + (f" from {loc}" if loc else "")
                             + f". HeavyMusix Radio plays {len(songs)} of their song{'s' if len(songs) != 1 else ''}.")
    links = {k: v for k, v in (b.get("links") or {}).items() if v}
    link_html = "".join(f'<a class="btn ghost" href="{esc(v)}">{esc("Band merch" if k == "merch" else k.capitalize())}</a>'
                        for k, v in links.items())
    on_eps = [e for e in live if any(s.get("b") == key for s in e.get("songs", []))]
    song_list = "".join(
        f'<li>{play_button(s["v"], b["name"] + " – " + s["t"])}'
        f'<span class="sinfo"><strong>{esc(s["t"])}</strong></span></li>' for s in songs)
    body = f"""<section class="hero"><div class="wrap">
  <p class="kicker">{'HeavyMusix unsigned pick' if b.get('unsigned') else 'On HeavyMusix Radio'}</p>
  <h1>{esc(b['name'])}</h1>
  <p class="lead">{esc(' · '.join(bits))}</p>
  <p>{esc(intro)}</p>
  {f'<div class="btns">{link_html}</div>' if link_html else ''}
  <h2 class="sub">{len(songs)} song{'s' if len(songs) != 1 else ''} on HeavyMusix Radio</h2>
  <ul class="songs">{song_list}</ul>
  {('<h2 class="sub">' + esc(b['name']) + ' in the news</h2><ul class="morenews">' + ''.join(f'<li><a href="news/{slug_of(m)}.html">{esc(m["title"])}</a><span class="wsrc">{fmt_date(m["date"])}</span></li>' for m in story_bands.get(key, [])[:8]) + '</ul>') if story_bands.get(key) else ''}
  <div class="sharebar"><button type="button" class="sharebtn" data-share>Share this band</button></div>
  <details class="followbox"><summary>In {esc(b['name'])}? Add the HeavyMusix Radio badge to your site</summary>
    <p><img src="assets/badge.svg" alt="Played on HeavyMusix Radio" width="240" height="64"></p>
    <p>Copy this into your website or link page:</p>
    <pre class="snippet">&lt;a href="{SITE}bands/{esc(key)}.html"&gt;&lt;img src="{SITE}assets/badge.svg" alt="Played on HeavyMusix Radio" width="240" height="64"&gt;&lt;/a&gt;</pre>
  </details>
  {('<p class="wupd">Played on ' + ', '.join(f'<a href="episodes/{e["n"]}.html">Show #{e["n"]}</a>' for e in on_eps) + '.</p>') if on_eps else ''}
  <div class="btns"><a class="btn ghost" href="bands.html">Find another band</a></div>
</div></section>"""
    desc = (f"{b['name']}: metal from {loc}. Listen to {len(songs)} song{'s' if len(songs) != 1 else ''} free on HeavyMusix Radio."
            if loc else f"{b['name']} on HeavyMusix Radio: listen to {len(songs)} songs free.")
    ld = {"@context": "https://schema.org", "@type": "MusicGroup", "name": b["name"], "url": f"{SITE}bands/{key}.html"}
    ld["genre"] = "Metal"
    if loc: ld["foundingLocation"] = {"@type": "Place", "name": loc}
    page(f"bands/{key}.html", f"{b['name']} | Metal{' from ' + (b.get('city') or b.get('country')) if (b.get('city') or b.get('country')) else ''} | HeavyMusix",
         cut(desc, 160), body, nav="bands.html", ld=[ld, crumbs(("Bands", "bands.html"), (b["name"], f"bands/{key}.html"))])
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
         cut(f"{e['title']}: {names}", 160), body, nav="show.html")
    pages.append((f"episodes/{e['n']}.html", (e.get("live") or TODAY.isoformat())[:10]))

# ---------------------------------------------------------------- Arizona shows this week
VENUES = js_data("venues.js", "VENUES") if os.path.exists("venues.js") else {}
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
        f'{datetime.date.fromisoformat(s["date"]).strftime("%a, %b %-d")} &middot; {esc(s["venue"])}, {esc(s["city"])}</span>{venue_html(s["venue"])}</li>'
        for s in lst) + "</ul>"


def venue_html(name):
    """Address, tap-to-call and Directions (same markup as venueDetails() in venues.js)."""
    v = VENUES.get(name)
    if not v:
        return ""
    full = f'{v["address"]}, {v["city"]}, AZ {v.get("zip", "")}'.strip()
    maps = "https://www.google.com/maps/dir/?api=1&destination=" + quote(f"{name}, {full}", safe="")
    call = (f'<a class="vcall" href="tel:+1{re.sub(r"[^0-9]", "", v["phone"])}" aria-label="Call {esc(name)} at {esc(v["phone"])}">&#9742;&#xFE0E; {esc(v["phone"])}</a>'
            if v.get("phone") else "")
    return (f'<span class="vdet"><span class="vaddr">{esc(full)}</span><span class="vlinks">{call}'
            f'<a class="vdir" href="{maps}" target="_blank" rel="noopener" aria-label="Directions to {esc(name)} (opens Google Maps in a new tab)">&#10148;&#xFE0E; Directions</a></span></span>')


cities = sorted({s["city"] for s in shows})
body = f"""<section class="hero"><div class="wrap">
  <p class="kicker">Arizona metal</p>
  <h1 class="compact">Metal shows in Phoenix and Arizona this week</h1>
  <p class="lead">Every heavy show we know about in Phoenix, Tempe, Mesa, Tucson and around Arizona. Updated every day. Week of {TODAY.strftime('%B %-d, %Y')}.</p>
  <h2 class="sub">This week: {TODAY.strftime('%a, %b %-d')} to {(TODAY + datetime.timedelta(days=6)).strftime('%a, %b %-d')}</h2>
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
                        "address": {"@type": "PostalAddress", **({"streetAddress": VENUES[s["venue"]]["address"], "postalCode": VENUES[s["venue"]].get("zip", "")} if s["venue"] in VENUES else {}), "addressLocality": s["city"],
                                    "addressRegion": "AZ", "addressCountry": "US"}},
           "performer": [{"@type": "MusicGroup", "name": p.strip()} for p in s["bands"].split(",") if p.strip()],
           "image": SITE + "og/default.png",
           "description": f"{s['bands']} live at {s['venue']} in {s['city']}, Arizona.",
           "organizer": {"@type": "Organization", "name": s["venue"]}}
          for s in shows[:40]]
page("arizona-metal-shows.html", "Metal shows in Phoenix & Arizona this week | HeavyMusix",
     f"Metal concerts in Phoenix, Tempe, Mesa, Tucson and across Arizona this week and coming up. Updated daily. {len(shows)} shows listed.",
     body, nav="arizona-metal-shows.html", ld=events or None)
pages.append(("arizona-metal-shows.html", TODAY.isoformat()))

shutil.rmtree("genres", ignore_errors=True)   # genre pages retired Nov 21, 2026; old links land on 404.html, which sends them to Find a band

# ---------------------------------------------------------------- this week in metal (rolling 7 days)
week_ago = (TODAY - datetime.timedelta(days=7)).isoformat()
recent = [n for n in news if n["date"] > week_ago and n.get("tag") not in ("Site", "Coming soon")]
groups = {}
for n in recent:
    groups.setdefault(n["tag"], []).append(n)
sections = "".join(f'<h2 class="sub">{esc(t)}</h2><ul class="morenews">' +
                   "".join(f'<li><a href="news/{slug_of(n)}.html">{esc(n["title"])}</a><span class="wsrc">{fmt_date(n["date"])}</span></li>' for n in lst) +
                   "</ul>" for t, lst in groups.items())
body = f"""<section class="hero"><div class="wrap">
  <p class="kicker">Week in review</p>
  <h1>This week in metal</h1>
  <p class="lead">The {len(recent)} biggest metal stories of the past seven days, from around the world and the Arizona desert. Updated every day.</p>
  {sections or '<p class="muted">New stories land every morning.</p>'}
  <div class="sharebar"><button type="button" class="sharebtn" data-share>Share this week in metal</button><a class="sharebtn" href="news.html">All news</a></div>
</div></section>"""
share_picture("og/week.png", "This week in metal", f"heavymusix.com  ·  {len(recent)} stories  ·  week of {TODAY.strftime('%B %-d, %Y')}", force=True)
page("this-week-in-metal.html", f"This week in metal: {len(recent)} stories | HeavyMusix",
     cut(f"The biggest metal news of the week: {', '.join(n['title'] for n in recent[:3])}", 158), body, nav="news.html", image="og/week.png")
pages.append(("this-week-in-metal.html", TODAY.isoformat()))

# ---------------------------------------------------------------- today in metal history (one page per day of the year)
try:
    HIST = js_data("history.js", "HISTORY")
except Exception:
    HIST = {}
fresh_dir("history")
for key, items in sorted(HIST.items()):
    m, d = map(int, key.split("-"))
    label = datetime.date(2000, m, d).strftime("%B %-d")
    rows = "".join(
        f'<li><strong>{h["year"]} &middot; {esc(h["type"])}</strong><span>{esc(h["text"])}'
        + (f' <a href="bands/{esc(h["band"])}.html">Listen on HeavyMusix Radio</a>' if h.get("band") and os.path.exists(f"bands/{h['band']}.html") else "")
        + f'</span><span class="wsrc">Source: {esc(h.get("source", ""))}</span></li>'
        for h in sorted(items, key=lambda h: h["year"]))
    prev_d = datetime.date(2000, m, d) - datetime.timedelta(days=1)
    next_d = datetime.date(2000, m, d) + datetime.timedelta(days=1)
    nav = "".join(f'<a class="btn ghost" href="history/{x.strftime("%m-%d")}.html">{x.strftime("%B %-d")}</a>'
                  for x in (prev_d, next_d) if x.strftime("%m-%d") in HIST)
    body = f"""<section class="hero"><div class="wrap">
  <p class="kicker">Today in metal history</p>
  <h1>{esc(label)} in metal history</h1>
  <p class="lead">Albums, birthdays, band beginnings and big moments in metal on {esc(label)}, checked against two sources each.</p>
  <ul class="morenews">{rows}</ul>
  <div class="sharebar"><button type="button" class="sharebtn" data-share>Share {esc(label)} in metal</button></div>
  <div class="btns">{nav}<a class="btn ghost" href="index.html">Today on HeavyMusix</a></div>
</div></section>"""
    first = sorted(items, key=lambda h: h["year"])[0]
    share_picture(f"og/history-{key}.png", f"{label} in metal history", f"heavymusix.com  ·  {len(items)} moment{'s' if len(items) != 1 else ''} from {first['year']} on")
    page(f"history/{key}.html", f"{label} in metal history: albums, birthdays and more | HeavyMusix",
         cut(f"What happened in metal on {label}: " + "; ".join(h["text"].rstrip(".") for h in items[:2]) + ".", 155), body, nav="index.html#history", image=f"og/history-{key}.png")
    pages.append((f"history/{key}.html", TODAY.isoformat()))

# ---------------------------------------------------------------- sitemap
MAIN = ["", "news.html", "show.html", "bands.html", "arizona.html", "series.html",
        "submit.html", "shop.html", "about.html", "checklist-ep1.html", "search.html", "ideas.html", "privacy.html", "newsletter.html"]
urls = [(p, TODAY.isoformat()) for p in MAIN] + pages
with open("sitemap.xml", "w", encoding="utf-8") as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
    for p, d in urls:
        f.write(f"  <url><loc>{esc(SITE + quote(p))}</loc><lastmod>{d}</lastmod></url>\n")
    f.write("</urlset>\n")

recent = [n for n in news if (TODAY - datetime.date.fromisoformat(n["date"])).days <= 2]
with open("news-sitemap.xml", "w", encoding="utf-8") as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">\n')
    for n in recent:
        f.write(f"  <url><loc>{esc(SITE + 'news/' + quote(slug_of(n)) + '.html')}</loc><news:news>"
                f"<news:publication><news:name>HeavyMusix</news:name><news:language>en</news:language></news:publication>"
                f"<news:publication_date>{n['date']}T05:00:00-07:00</news:publication_date>"
                f"<news:title>{esc(n['title'])}</news:title></news:news></url>\n")
    f.write("</urlset>\n")

print(f"Built {len(news)} stories, {sum(1 for p, _ in pages if p.startswith('bands/'))} band pages, "
      f"{len(live)} episodes, {len(shows)} Arizona shows; feed.xml and sitemap.xml ({len(urls)} pages).")
