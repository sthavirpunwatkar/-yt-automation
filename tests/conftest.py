import io
import os
import shutil
import urllib.request
import urllib.error
import socket
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

def pytest_addoption(parser):
    parser.addoption("--mode", action="store", default="mocked", choices=["mocked", "live"])
    parser.addoption("--tier", action="store", default="all")

@pytest.fixture(scope="session", autouse=True)
def dummy_assets_paths():
    assets_dir = Path(__file__).parent / "assets"
    return {
        "image": assets_dir / "dummy_image.jpg",
        "audio": assets_dir / "dummy_audio.mp3",
        "video": assets_dir / "dummy_video.mp4",
    }

@pytest.fixture(autouse=True)
def mock_edge_tts(request, dummy_assets_paths):
    if request.config.getoption("--mode") == "live":
        yield
        return
    
    def fake_synthesize_full(text, out_path, voice=None):
        shutil.copyfile(dummy_assets_paths["audio"], out_path)
        words = text.split()
        timings = [{
            "text": text,
            "offset_ms": 0,
            "duration_ms": 2000
        }]
        return 2.0, timings

    with patch("pipeline.edge_tts_synth.synthesize_full", side_effect=fake_synthesize_full) as mock:
        yield mock

@pytest.fixture(autouse=True)
def mock_groq(request):
    if request.config.getoption("--mode") == "live":
        yield
        return

    def fake_generate_short_pack(preset, topic_hint=None, channel_id=None, extra_context=None):
        return {
            "youtube_title": "Mock Title",
            "youtube_description": "Mock Description",
            "full_narration": "This is a mock narration for E2E testing.",
            "image_prompts": ["Prompt 1", "Prompt 2", "Prompt 3"],
            "visual_search_queries": ["Query 1", "Query 2", "Query 3"],
            "variants": {
                "en": {
                    "youtube_title": "English Title",
                    "youtube_description": "English Description",
                    "full_narration": "This is English narration."
                },
                "hi": {
                    "youtube_title": "Hindi Title",
                    "youtube_description": "Hindi Description",
                    "full_narration": "This is Hindi narration."
                }
            }
        }

    with patch("pipeline.groq_script.generate_short_pack", side_effect=fake_generate_short_pack) as mock:
        yield mock

@pytest.fixture(autouse=True)
def mock_deapi_images(request, dummy_assets_paths):
    if request.config.getoption("--mode") == "live":
        yield
        return

    def fake_save_scene_image(index, prompt, out_path, **kwargs):
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(dummy_assets_paths["image"], out_path)
        return "ok", "mocked"

    with patch("pipeline.images.save_scene_image", side_effect=fake_save_scene_image) as mock:
        yield mock

@pytest.fixture(autouse=True)
def mock_ddg_images(request, dummy_assets_paths):
    if request.config.getoption("--mode") == "live":
        yield
        return

    def fake_fetch_web_image(query, out_path):
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(dummy_assets_paths["image"], out_path)
        return "ok", "http://mocked-ddg-url.com/image.jpg"

    def fake_search_and_download(prompt):
        return dummy_assets_paths["image"].read_bytes()

    with patch("pipeline.web_images.fetch_web_image", side_effect=fake_fetch_web_image) as mock_fetch, \
         patch("pipeline.images._search_and_download", side_effect=fake_search_and_download) as mock_search:
        yield mock_fetch

@pytest.fixture(autouse=True)
def mock_httpx_deapi(request, dummy_assets_paths):
    if request.config.getoption("--mode") == "live":
        yield
        return

    import httpx
    original_post = httpx.Client.post
    original_get = httpx.Client.get

    def mock_post(self, url, *args, **kwargs):
        url_str = str(url)
        req = httpx.Request("POST", url)
        if "txt2video" in url_str:
            resp = httpx.Response(200, json={"data": {"request_id": "mock_req_123"}}, request=req)
            return resp
        return original_post(self, url, *args, **kwargs)

    def mock_get(self, url, *args, **kwargs):
        url_str = str(url)
        req = httpx.Request("GET", url)
        if "request-status/mock_req_123" in url_str:
            resp = httpx.Response(200, json={"data": {"status": "completed", "result_url": "http://mock.url/vid.mp4"}}, request=req)
            return resp
        elif "mock.url/vid.mp4" in url_str:
            resp = httpx.Response(200, content=dummy_assets_paths["video"].read_bytes(), request=req)
            return resp
        elif "picsum.photos" in url_str or "example.com" in url_str:
            resp = httpx.Response(200, content=dummy_assets_paths["image"].read_bytes(), headers={"Content-Type": "image/jpeg"}, request=req)
            return resp
        return original_get(self, url, *args, **kwargs)

    with patch.object(httpx.Client, "post", mock_post), \
         patch.object(httpx.Client, "get", mock_get):
        yield

@pytest.fixture(autouse=True)
def mock_urllib_downloader(request, dummy_assets_paths):
    if request.config.getoption("--mode") == "live":
        yield
        return

    class MockResponse:
        def __init__(self, content, headers=None):
            self.content = content
            self.headers = headers or {"Content-Type": "image/jpeg"}
        def read(self, *args, **kwargs):
            return self.content
        def getcode(self):
            return 200
        def info(self):
            class Info:
                def get(self, name, default=""):
                    if name.lower() == "content-type":
                        return self.headers.get("Content-Type", default)
                    return default
            return Info()
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    # Simple headers mock
    headers_mock = MagicMock()
    headers_mock.get.return_value = "image/jpeg"

    def fake_urlopen(req, *args, **kwargs):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        
        if "fail_404" in url:
            # We must pass valid arguments to HTTPError
            fp = io.BytesIO(b"Not Found")
            raise urllib.error.HTTPError(url, 404, "Not Found", headers_mock, fp)
        elif "fail_403" in url:
            fp = io.BytesIO(b"Forbidden")
            raise urllib.error.HTTPError(url, 403, "Forbidden", headers_mock, fp)
        elif "timeout" in url:
            raise socket.timeout("timeout")
        elif "html_content" in url:
            return MockResponse(b"<html>Error Page</html>", {"Content-Type": "text/html"})
        
        # Default success
        return MockResponse(dummy_assets_paths["image"].read_bytes())

    with patch("urllib.request.urlopen", side_effect=fake_urlopen) as mock:
        yield mock

@pytest.fixture(autouse=True)
def mock_uploads(request):
    if request.config.getoption("--mode") == "live":
        yield
        return

    with patch("pipeline.youtube_upload.upload_short", return_value="mock_yt_vid_id") as m_yt, \
         patch("pipeline.instagram_upload.publish_instagram_reel", return_value="mock_insta_media_id") as m_insta, \
         patch("pipeline.instagram_upload.publish_facebook_reel", return_value="mock_fb_video_id") as m_fb:
        yield (m_yt, m_insta, m_fb)
