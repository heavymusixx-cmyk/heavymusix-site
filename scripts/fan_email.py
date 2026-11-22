"""Weekly fan email: every Friday, sends "This week in HeavyMusix" to the Brevo list
"HeavyMusix Fans" (fans who signed up and confirmed by email).

Content: the week's top stories, "New on HeavyMusix" (site updates from
social/updates.json), newly announced Arizona shows coming up, and a link back to
the radio. Built only from the site's own data (news.js, shows.js, updates.json).

Announcements: `python scripts/fan_email.py --announce` sends the one-off email in
social/announcement.json (launch day, band submissions open, a merch drop...) once,
after the owner approves it. Run it from the "Weekly fan email" workflow with
"announce" switched on.

Needs the GitHub secret BREVO_API_KEY. Without it the robot does nothing.
Sender: HeavyMusix <info@heavymusix.com> (must be a verified sender in Brevo).
Every email carries our own one-click unsubscribe link at the top and bottom ({{ unsubscribe }},
filled in by Brevo); Brevo also adds its postal footer and the List-Unsubscribe header.
"""
import datetime as dt
import html
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

API = "https://api.brevo.com/v3"
LIST_NAME = "HeavyMusix Fans"
SITE = "https://heavymusix.com/"
AZ = dt.timezone(dt.timedelta(hours=-7))
esc = lambda s: html.escape(str(s or ""), quote=True)


def js_data(file, var):
    code = (f"eval(require('fs').readFileSync({json.dumps(file)},'utf8')"
            f"+';process.stdout.write(JSON.stringify({var}))')")
    return json.loads(subprocess.check_output(["node", "-e", code], text=True))


def slug_of(n):  # same as build_pages.py / news.js
    return n.get("slug") or (n["date"] + "-" + re.sub(r"[^a-z0-9]+", "-", n["title"].lower()).strip("-")[:60])  # "slug" keeps the old address when a title is reworded


def call(method, path, key, body=None):
    req = urllib.request.Request(API + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"api-key": key, "accept": "application/json",
                                          "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
        return json.loads(raw) if raw else {}


def build(today):
    news = js_data("news.js", "NEWS")
    shows = js_data("shows.js", "SHOWS")
    week_ago = (today - dt.timedelta(days=7)).isoformat()
    stories = [n for n in news if n["date"] > week_ago]
    lead = [n for n in stories if n.get("tag") != "Throwback"][:6] + [n for n in stories if n.get("tag") == "Throwback"][:1]
    try:
        ups = json.load(open("social/updates.json", encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        ups = []
    ups = [u for u in ups if u.get("date", "") > week_ago][:5]
    soon = [s for s in shows if today.isoformat() <= s["date"] <= (today + dt.timedelta(days=21)).isoformat()][:8]
    red, bone = "#a3121b", "#e8e2d4"
    rows = "".join(
        f'<tr><td style="padding:14px 0;border-bottom:1px solid #2a2324">'
        f'<div style="font:700 12px Arial,sans-serif;color:#ff4a52;text-transform:uppercase;letter-spacing:.06em">{esc(n.get("tag", "News"))}</div>'
        f'<a href="{SITE}news/{slug_of(n)}.html?ref=email" style="font:700 19px Georgia,serif;color:{bone};text-decoration:none">{esc(n["title"])}</a>'
        f'<div style="font:15px/1.5 Arial,sans-serif;color:#cfc7b4;margin-top:6px">{esc(n["text"][0][:220])}{"..." if len(n["text"][0]) > 220 else ""}</div></td></tr>'
        for n in lead)
    show_rows = "".join(
        f'<li style="margin:6px 0"><strong>{esc(s["bands"])}</strong> &middot; {esc(s["venue"])}, {esc(s["city"])} &middot; {esc(s["date"])}</li>'
        for s in soon)
    up_rows = "".join(
        f'<li style="margin:6px 0">{esc(u["text"])}' + (f' <a href="{esc(u["link"])}{"&" if "?" in u["link"] else "?"}ref=email" style="color:#ff4a52">See it</a>' if u.get("link") else "") + '</li>'
        for u in ups)
    body = f"""<div style="background:#050404;padding:24px 0"><table role="presentation" width="100%" style="max-width:600px;margin:0 auto;background:#0b0a0a;border:3px solid {bone}">
<tr><td style="padding:8px 22px;font:13px Arial,sans-serif;color:#b9b0a2;text-align:right">Not into it anymore? <a href="{{{{ unsubscribe }}}}" style="color:#e8e2d4">Unsubscribe in one click</a>, no hard feelings.</td></tr>
<tr><td style="background:{red};padding:18px 22px;font:700 30px Georgia,serif;color:#fff">HeavyMusix <span style="font-size:16px;font-weight:400">&middot; This week in metal</span></td></tr>
<tr><td style="padding:8px 22px 0"><table role="presentation" width="100%">{rows}</table></td></tr>
{f'<tr><td style="padding:18px 22px 0;font:15px/1.5 Arial,sans-serif;color:{bone}"><div style="font:700 18px Georgia,serif;margin-bottom:6px">New on HeavyMusix</div><ul style="padding-left:18px;margin:0">{up_rows}</ul></td></tr>' if ups else ''}
{f'<tr><td style="padding:18px 22px;font:15px/1.5 Arial,sans-serif;color:{bone}"><div style="font:700 18px Georgia,serif;margin-bottom:6px">Coming up in Arizona</div><ul style="padding-left:18px;margin:0">{show_rows}</ul></td></tr>' if soon else ''}
<tr><td style="padding:18px 22px 24px;font:15px/1.5 Arial,sans-serif;color:{bone}">
<a href="{SITE}?ref=email" style="display:inline-block;background:{red};color:#fff;font:700 16px Arial,sans-serif;padding:12px 20px;text-decoration:none;border:2px solid {bone}">&#9654; Listen to HeavyMusix Radio</a>
<p style="margin:16px 0 0;color:#cfc7b4">In a band? Band submissions open soon at <a href="https://heavymusix.com/submit?ref=email" style="color:#cfc7b4">heavymusix.com/submit</a>. Free, always, and every band gets a turn.<br>&mdash; Heavy</p></td></tr>
<tr><td style="padding:14px 22px 20px;border-top:1px solid #333;font:13px/1.5 Arial,sans-serif;color:#b9b0a2">You get this because you signed up at heavymusix.com. Want out? <a href="{{{{ unsubscribe }}}}" style="color:#e8e2d4">Unsubscribe in one click</a>, or just reply &ldquo;unsubscribe.&rdquo; You&rsquo;re always welcome back.</td></tr>
</table></div>"""
    lead_title = lead[0]["title"] if lead else "This week in metal"
    subject = ("This week in metal: " + lead_title)[:120]
    return subject, body, len(lead)


def build_announcement():
    """One-off email from social/announcement.json: {"id", "subject", "title", "text": [paragraphs], "link", "button"}."""
    a = json.load(open("social/announcement.json", encoding="utf-8"))
    red, bone = "#a3121b", "#e8e2d4"
    link = a["link"] + ("&" if "?" in a["link"] else "?") + "ref=announce"
    paras = "".join(f'<p style="margin:0 0 12px">{esc(t)}</p>' for t in a["text"])
    body = f"""<div style="background:#050404;padding:24px 0"><table role="presentation" width="100%" style="max-width:600px;margin:0 auto;background:#0b0a0a;border:3px solid {bone}">
<tr><td style="padding:8px 22px;font:13px Arial,sans-serif;color:#b9b0a2;text-align:right">Not into it anymore? <a href="{{{{ unsubscribe }}}}" style="color:#e8e2d4">Unsubscribe in one click</a>, no hard feelings.</td></tr>
<tr><td style="background:{red};padding:18px 22px;font:700 30px Georgia,serif;color:#fff">HeavyMusix</td></tr>
<tr><td style="padding:22px;font:16px/1.55 Arial,sans-serif;color:{bone}"><div style="font:700 26px Georgia,serif;margin-bottom:12px">{esc(a["title"])}</div>{paras}
<a href="{esc(link)}" style="display:inline-block;background:{red};color:#fff;font:700 16px Arial,sans-serif;padding:12px 20px;text-decoration:none;border:2px solid {bone}">{esc(a.get("button", "See it on HeavyMusix"))}</a>
<p style="margin:16px 0 0;color:#cfc7b4">&mdash; Heavy</p></td></tr>
<tr><td style="padding:14px 22px 20px;border-top:1px solid #333;font:13px/1.5 Arial,sans-serif;color:#b9b0a2">You get this because you signed up at heavymusix.com. Want out? <a href="{{{{ unsubscribe }}}}" style="color:#e8e2d4">Unsubscribe in one click</a>, or just reply &ldquo;unsubscribe.&rdquo; You&rsquo;re always welcome back.</td></tr></table></div>"""
    return a["subject"][:120], body, a.get("id", "")


def main():
    key = os.environ.get("BREVO_API_KEY", "").strip()
    today = dt.datetime.now(AZ).date()
    announce = "--announce" in sys.argv
    if announce:
        if not os.path.exists("social/announcement.json"):
            print("No social/announcement.json; nothing to announce."); return
        subject, body, aid = build_announcement()
        sent = []
        try:
            sent = json.load(open("social/announced.json", encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            pass
        if aid in sent and "--preview" not in sys.argv:
            print(f"Announcement {aid} was already sent; not sending it twice."); return
        count = 99
    else:
        subject, body, count = build(today)
    if "--preview" in sys.argv:
        open("announcement-preview.html" if announce else "fan-email-preview.html", "w", encoding="utf-8").write(body)
        print(f"Preview written ({count} stories): {subject}")
        return
    if not key:
        print("BREVO_API_KEY is not set yet; the weekly fan email is waiting for the owner's Brevo key.")
        return
    if count < 3:
        print("Fewer than 3 stories this week; skipping the email.")
        return
    try:
        lists = call("GET", "/contacts/lists?limit=50", key).get("lists", [])
        lst = next((l for l in lists if l.get("name", "").strip().lower() == LIST_NAME.lower()), None)
        if not lst:
            print(f'No Brevo list named "{LIST_NAME}" yet; nothing sent.')
            return
        if not lst.get("uniqueSubscribers") and not lst.get("totalSubscribers"):
            print("The fan list has no subscribers yet; nothing sent.")
            return
        camp = call("POST", "/emailCampaigns", key, {
            "name": (f"Announcement {aid}" if announce else f"Weekly fan email {today.isoformat()}"),
            "subject": subject,
            "sender": {"name": "HeavyMusix", "email": "info@heavymusix.com"},
            "replyTo": "info@heavymusix.com",
            "htmlContent": "<html><body style=\"margin:0\">" + body + "</body></html>",
            "recipients": {"listIds": [lst["id"]]},
        })
        call("POST", f"/emailCampaigns/{camp['id']}/sendNow", key)
        print(f"Sent to list {lst['id']}: {subject}")
        if announce:
            json.dump(sent + [aid], open("social/announced.json", "w", encoding="utf-8"), indent=1)
    except urllib.error.HTTPError as e:
        print(f"Brevo error {e.code}: {e.read().decode(errors='replace')[:400]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
