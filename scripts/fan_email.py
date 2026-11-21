"""Weekly fan email: every Friday, sends "This week in HeavyMusix" to the Brevo list
"HeavyMusix Fans" (fans who signed up and confirmed by email).

Content: the week's top stories, newly announced Arizona shows coming up, and a
link back to the radio. Built only from the site's own data (news.js, shows.js).

Needs the GitHub secret BREVO_API_KEY. Without it the robot does nothing.
Sender: HeavyMusix <info@heavymusix.com> (must be a verified sender in Brevo).
Brevo adds the unsubscribe link and the postal footer itself.
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
    return n["date"] + "-" + re.sub(r"[^a-z0-9]+", "-", n["title"].lower()).strip("-")[:60]


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
    body = f"""<div style="background:#050404;padding:24px 0"><table role="presentation" width="100%" style="max-width:600px;margin:0 auto;background:#0b0a0a;border:3px solid {bone}">
<tr><td style="background:{red};padding:18px 22px;font:700 30px Georgia,serif;color:#fff">HeavyMusix <span style="font-size:16px;font-weight:400">&middot; This week in metal</span></td></tr>
<tr><td style="padding:8px 22px 0"><table role="presentation" width="100%">{rows}</table></td></tr>
{f'<tr><td style="padding:18px 22px;font:15px/1.5 Arial,sans-serif;color:{bone}"><div style="font:700 18px Georgia,serif;margin-bottom:6px">Coming up in Arizona</div><ul style="padding-left:18px;margin:0">{show_rows}</ul></td></tr>' if soon else ''}
<tr><td style="padding:18px 22px 24px;font:15px/1.5 Arial,sans-serif;color:{bone}">
<a href="{SITE}?ref=email" style="display:inline-block;background:{red};color:#fff;font:700 16px Arial,sans-serif;padding:12px 20px;text-decoration:none;border:2px solid {bone}">&#9654; Listen to HeavyMusix Radio</a>
<p style="margin:16px 0 0;color:#cfc7b4">In a band? Band submissions open soon at <a href="https://heavymusix.com/submit?ref=email" style="color:#cfc7b4">heavymusix.com/submit</a>. Free, always, and every band gets a turn.<br>&mdash; Heavy</p></td></tr>
</table></div>"""
    lead_title = lead[0]["title"] if lead else "This week in metal"
    subject = ("This week in metal: " + lead_title)[:120]
    return subject, body, len(lead)


def main():
    key = os.environ.get("BREVO_API_KEY", "").strip()
    today = dt.datetime.now(AZ).date()
    subject, body, count = build(today)
    if "--preview" in sys.argv:
        open("fan-email-preview.html", "w", encoding="utf-8").write(body)
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
            "name": f"Weekly fan email {today.isoformat()}",
            "subject": subject,
            "sender": {"name": "HeavyMusix", "email": "info@heavymusix.com"},
            "replyTo": "info@heavymusix.com",
            "htmlContent": "<html><body style=\"margin:0\">" + body + "</body></html>",
            "recipients": {"listIds": [lst["id"]]},
        })
        call("POST", f"/emailCampaigns/{camp['id']}/sendNow", key)
        print(f"Sent to list {lst['id']}: {subject}")
    except urllib.error.HTTPError as e:
        print(f"Brevo error {e.code}: {e.read().decode(errors='replace')[:400]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
