import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

token_path = Path("secrets/youtube_token.json")
if not token_path.exists():
    print("Token not found locally.")
    exit(1)

token_data = json.loads(token_path.read_text())
creds = Credentials(
    token=token_data.get("token"),
    refresh_token=token_data.get("refresh_token"),
    token_uri=token_data.get("token_uri"),
    client_id=token_data.get("client_id"),
    client_secret=token_data.get("client_secret"),
    scopes=token_data.get("scopes")
)

try:
    youtube = build("youtube", "v3", credentials=creds)
    req = youtube.channels().list(mine=True, part="id,snippet")
    resp = req.execute()
    
    items = resp.get("items", [])
    if not items:
        print("NO_CHANNEL")
    else:
        for item in items:
            print("FOUND_CHANNEL:", item["snippet"]["title"])
except Exception as e:
    print("ERROR:", e)
