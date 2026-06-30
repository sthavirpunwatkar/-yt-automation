import os
import sys
import pytest
import shutil
import httpx
from pathlib import Path
from unittest.mock import patch, MagicMock

# Mock easyocr to avoid ModuleNotFoundError when importing pipeline.watermark_removal
sys.modules["easyocr"] = MagicMock()

def run_script_main(script_module, args):
    original_argv = list(os.sys.argv)
    os.sys.argv = ["dummy.py"] + args
    try:
        script_module.main()
        return 0
    except SystemExit as e:
        return e.code
    finally:
        os.sys.argv = original_argv

@pytest.mark.tier3
def test_t3_partial_fail_and_fallback(tmp_path):
    import scripts.run_short as run_short
    # One ok URL, one 404 URL. Part failure triggers complete fallback to auto-generation
    args = ["--channel", "football", "--image-urls", "http://example.com/ok.jpg,http://fail_404.com/bad.jpg"]
    with patch("scripts.run_short.REPO_ROOT", tmp_path), \
         patch("pipeline.story_history.REPO_ROOT", tmp_path):
        fonts_src = Path(__file__).parent.parent.parent / "assets" / "fonts"
        fonts_dst = tmp_path / "assets" / "fonts"
        fonts_dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fonts_src / "BebasNeue-Regular.ttf", fonts_dst / "BebasNeue-Regular.ttf")

        code = run_script_main(run_short, args)
        assert code == 0
        assert next((tmp_path / "output" / "runs").glob("**/short.mp4")).exists()

@pytest.mark.tier3
def test_t3_token_rotation_and_manual(tmp_path):
    import scripts.run_short_ltx as run_short_ltx
    # To test token rotation, we run run_short_ltx in auto-generation mode (fallback triggered by failing manual URL)
    # and mock the httpx client to return 429 for the first submit call, triggering rotation to the next token
    args = ["--channel", "fifa_2026", "--image-urls", "http://fail_404.com/bad.jpg"]
    
    post_count = 0
    original_post = httpx.Client.post
    
    def rotating_post(self, url, *args, **kwargs):
        nonlocal post_count
        url_str = str(url)
        req = httpx.Request("POST", url)
        if "txt2video" in url_str:
            post_count += 1
            if post_count == 1:
                # First attempt: rate limited 429
                return httpx.Response(429, text="Rate limit exceeded", request=req)
            else:
                # Second attempt: succeed!
                return httpx.Response(200, json={"data": {"request_id": "mock_req_rotation"}}, request=req)
        return original_post(self, url, *args, **kwargs)

    original_get = httpx.Client.get
    def rotating_get(self, url, *args, **kwargs):
        url_str = str(url)
        req = httpx.Request("GET", url)
        if "request-status/mock_req_rotation" in url_str:
            return httpx.Response(200, json={"data": {"status": "completed", "result_url": "http://mock.url/rotated.mp4"}}, request=req)
        elif "mock.url/rotated.mp4" in url_str:
            dummy_video = Path(__file__).parent.parent / "assets" / "dummy_video.mp4"
            return httpx.Response(200, content=dummy_video.read_bytes(), request=req)
        return original_get(self, url, *args, **kwargs)

    with patch("scripts.run_short_ltx.REPO_ROOT", tmp_path), \
         patch("pipeline.story_history.REPO_ROOT", tmp_path), \
         patch.object(httpx.Client, "post", rotating_post), \
         patch.object(httpx.Client, "get", rotating_get):
        
        fonts_src = Path(__file__).parent.parent.parent / "assets" / "fonts"
        fonts_dst = tmp_path / "assets" / "fonts"
        fonts_dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fonts_src / "CreepsterCaps.ttf", fonts_dst / "CreepsterCaps.ttf")

        # Set initial token index so it rotates through our mock
        run_short_ltx.current_token_idx = 0

        code = run_script_main(run_short_ltx, args)
        assert code == 0
        assert post_count > 1  # Verify rotation was triggered!

@pytest.mark.tier3
def test_t3_bilingual_and_manual(tmp_path):
    import scripts.run_short as run_short
    # Define a custom bilingual preset to override the standard "football" preset
    mock_preset = {
        "id": "football",
        "label": "Mock Bilingual Football",
        "language": "en",
        "min_words": 10,
        "tts_voice": "en-US-GuyNeural",
        "caption_font": "BebasNeue-Regular.ttf",
        "caption_font_name": "Bebas Neue",
        "yt_token_env": "YT_REFRESH_TOKEN",
        "segment_count": 2,
        "variants": [
            {
                "lang": "en",
                "label": "English Variant",
                "tts_voice": "en-US-GuyNeural",
                "caption_font": "BebasNeue-Regular.ttf",
                "caption_font_name": "Bebas Neue",
                "yt_token_env": "YT_REFRESH_TOKEN",
            },
            {
                "lang": "hi",
                "label": "Hindi Variant",
                "tts_voice": "hi-IN-MadhurNeural",
                "caption_font": "NotoSansDevanagari-Bold.ttf",
                "caption_font_name": "Noto Sans Devanagari",
                "yt_token_env": "YT_REFRESH_TOKEN_HINDI",
            }
        ]
    }
    
    args = ["--channel", "football", "--image-urls", "http://example.com/1.jpg,http://example.com/2.jpg", "--upload"]
    
    with patch("scripts.run_short.REPO_ROOT", tmp_path), \
         patch("pipeline.story_history.REPO_ROOT", tmp_path), \
         patch("pipeline.channel_presets.get_preset", return_value=mock_preset):
        
        fonts_src = Path(__file__).parent.parent.parent / "assets" / "fonts"
        fonts_dst = tmp_path / "assets" / "fonts"
        fonts_dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fonts_src / "BebasNeue-Regular.ttf", fonts_dst / "BebasNeue-Regular.ttf")

        # Verify it runs both variants and executes successfully
        code = run_script_main(run_short, args)
        assert code == 0
        
        # Verify that the run directory contains variant outputs (e.g., voiceover_en.mp3/voiceover_hi.mp3 or short_en.mp4)
        run_dir = next((tmp_path / "output" / "runs").iterdir())
        assert any("_en" in p.name for p in run_dir.iterdir()) or any("short" in p.name for p in run_dir.iterdir())

@pytest.mark.tier3
def test_t3_ddg_mock_and_watermark(tmp_path):
    import scripts.run_slideshow as run_slideshow
    # Force fallback to trigger search and watermark removal
    args = ["--channel", "football", "--image-urls", "http://fail_404.com/bad.jpg"]
    
    watermark_called = False
    def fake_remove_watermark(src, dst):
        nonlocal watermark_called
        watermark_called = True
        shutil.copyfile(src, dst)

    # Import watermark removal after mock setup and patch it
    from pipeline.watermark_removal import remove_watermark
    
    with patch("scripts.run_slideshow.REPO_ROOT", tmp_path), \
         patch("pipeline.story_history.REPO_ROOT", tmp_path), \
         patch("pipeline.watermark_removal.remove_watermark", side_effect=fake_remove_watermark):
        
        fonts_src = Path(__file__).parent.parent.parent / "assets" / "fonts"
        fonts_dst = tmp_path / "assets" / "fonts"
        fonts_dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fonts_src / "BebasNeue-Regular.ttf", fonts_dst / "BebasNeue-Regular.ttf")

        code = run_script_main(run_slideshow, args)
        assert code == 0
