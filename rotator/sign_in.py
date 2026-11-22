"""
HeavyMusix: make a fresh YouTube sign-in for the GitHub robot. Signs in only; never touches the playlist.

How to use (on the laptop, once):
  1. Save this file into C:\\Playlist Rotator (next to client_secret.json).
  2. In that folder, click the address bar, type  cmd  and press Enter.
  3. Type  python sign_in.py  and press Enter.
  4. A browser opens: choose the HeavyMusix account and click Allow (or Continue).
  5. The new sign-in is copied to your clipboard. Paste it into GitHub:
     repo > Settings > Secrets and variables > Actions > YT_TOKEN > Update.
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SECRETS = os.path.join(HERE, "client_secret.json")
SCOPES = ["https://www.googleapis.com/auth/youtube"]

if not os.path.exists(SECRETS):
    sys.exit("client_secret.json is not in this folder. Put this file next to client_secret.json and try again.")
try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except ImportError:
    sys.exit("Missing tools. Run this first, then try again:\n  pip install google-api-python-client google-auth-oauthlib")

creds = InstalledAppFlow.from_client_secrets_file(SECRETS, SCOPES).run_local_server(port=0, prompt="select_account consent")
me = build("youtube", "v3", credentials=creds).channels().list(part="snippet", mine=True).execute().get("items", [])
name = me[0]["snippet"]["title"] if me else "(no channel)"
print(f"\nSigned in as YouTube channel: {name}")
if "heavymusix" not in name.lower().replace(" ", ""):
    sys.exit("That is not the HeavyMusix channel. Run it again and pick the HeavyMusix account.")
if not creds.refresh_token:
    sys.exit("Google did not give a lasting sign-in. Run it again; if it repeats, tell Claude.")
token = creds.to_json()
open(os.path.join(HERE, "token-for-github.txt"), "w").write(token)
try:
    subprocess.run("clip", input=token.encode(), check=True, shell=True)
    print("Copied to your clipboard. Now paste it into GitHub as the YT_TOKEN secret (Update).")
except Exception:
    print("Open token-for-github.txt in this folder, copy everything in it, and paste it into GitHub as YT_TOKEN.")
print("Then delete token-for-github.txt from this folder.")
