import json
from pathlib import Path
import httpx
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

token_path = Path("secrets/youtube_token.json")
token_data = json.loads(token_path.read_text())
creds = Credentials(
    token=token_data.get("token"),
    refresh_token=token_data.get("refresh_token"),
    token_uri=token_data.get("token_uri"),
    client_id=token_data.get("client_id"),
    client_secret=token_data.get("client_secret"),
    scopes=token_data.get("scopes")
)
creds.refresh(Request())

headers = {
    "Authorization": f"Bearer {creds.token}",
    "Accept": "application/json",
}

# Upload directly
url = "https://www.googleapis.com/upload/youtube/v3/videos?part=snippet,status"
video_data = Path("test.mp4").read_bytes()

metadata = {
    "snippet": {
        "title": "Test Title",
        "description": "Test Description",
        "categoryId": "24"
    },
    "status": {
        "privacyStatus": "private"
    }
}

# We can do a multipart upload
files = {
    "metadata": (None, json.dumps(metadata), "application/json"),
    "file": ("test.mp4", video_data, "video/mp4")
}

resp = httpx.post(url, headers=headers, files=files)
print(resp.status_code)
print(resp.text)
