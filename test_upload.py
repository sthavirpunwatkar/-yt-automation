import traceback
from pathlib import Path
from pipeline.youtube_upload import upload_short

try:
    vid = upload_short(
        Path("test.mp4"),
        "Test Upload",
        "Test description",
        privacy_status="private"
    )
    print("SUCCESS, vid =", vid)
except Exception as e:
    print("ERROR:")
    traceback.print_exc()
