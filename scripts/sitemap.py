"""Builds sitemap.xml so Google and Bing can find every page:
the main pages, every HeavyMusix news story, and every band page.
Run by the Music News robot (.github/workflows/metal-wire.yml)."""
import json, re, datetime
from urllib.parse import quote
from xml.sax.saxutils import escape

SITE = "https://heavymusix.com/"
PAGES = ["", "news.html", "show.html", "bands.html", "arizona.html", "series.html",
         "submit.html", "shop.html", "about.html", "checklist-ep1.html"]
today = datetime.date.today().isoformat()

def slug(date, title):  # same as slugOf() in news.js
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]
    return f"{date}-{s}"

urls = [(SITE + p, today) for p in PAGES]

src = open("news.js", encoding="utf-8").read()
for m in re.finditer(r'date:\s*"(\d{4}-\d\d-\d\d)",\s*tag:\s*"[^"]*",\s*title:\s*"((?:[^"\\]|\\.)*)"', src):
    date, title = m.group(1), m.group(2).replace('\\"', '"')
    urls.append((SITE + "article.html?p=" + quote(slug(date, title), safe=""), date))

try:
    for key in json.load(open("show/bands.json", encoding="utf-8")):
        urls.append((SITE + "band.html?b=" + quote(key, safe=""), today))
except FileNotFoundError:
    pass

out = ['<?xml version="1.0" encoding="UTF-8"?>',
       '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
seen = set()
for u, d in urls:
    if u in seen: continue
    seen.add(u)
    out.append(f"  <url><loc>{escape(u)}</loc><lastmod>{d}</lastmod></url>")
out.append("</urlset>")
open("sitemap.xml", "w", encoding="utf-8").write("\n".join(out) + "\n")
print(len(seen), "pages in sitemap.xml")
