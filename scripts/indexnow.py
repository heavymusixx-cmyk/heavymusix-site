"""Tell Bing and other IndexNow search engines about new and changed pages right away.

Run by the Build pages robot after it publishes. Reads the pages changed in the last commit.
The key file (8041d8c2080c95d0ab29c5b0fcde3bff.txt at the site root) proves we own heavymusix.com. Standard library only.
"""
import json, subprocess, sys, urllib.request

KEY = "8041d8c2080c95d0ab29c5b0fcde3bff"
SITE = "https://heavymusix.com/"

changed = subprocess.run(["git", "diff", "--name-only", "HEAD~1", "HEAD"], capture_output=True, text=True).stdout.split()
urls = [SITE + p for p in changed if p.endswith(".html") and p.split("/")[0] in ("news", "bands", "history", "genres", "episodes")]
urls += [SITE + p for p in ("news.html", "arizona-metal-shows.html", "this-week-in-metal.html") if p in changed]
urls.insert(0, SITE)
urls = list(dict.fromkeys(urls))[:1000]
body = json.dumps({"host": "heavymusix.com", "key": KEY, "keyLocation": SITE + KEY + ".txt", "urlList": urls}).encode()
req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body,
                             headers={"Content-Type": "application/json; charset=utf-8"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"IndexNow: sent {len(urls)} pages, answer {r.status}")
except Exception as e:
    print(f"IndexNow: not sent ({e})")   # never fail the build over this
    sys.exit(0)
