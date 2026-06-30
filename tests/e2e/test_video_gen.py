import os
import json
import pytest
import subprocess
import shutil
from pathlib import Path
from unittest.mock import patch

# Helper to run script's main
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

def get_media_properties(video_path):
    cmd = [
        "ffprobe", "-v", "error", "-show_streams", "-show_format",
        "-print_format", "json", str(video_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(res.stdout)

@pytest.mark.tier1
def test_t1_f3_video_output(tmp_path):
    import scripts.run_slideshow as run_slideshow
    # Run a simple short run with manual URLs
    args = ["--channel", "football", "--image-urls", "http://example.com/1.jpg,http://example.com/2.jpg"]
    
    with patch("scripts.run_slideshow.REPO_ROOT", tmp_path), \
         patch("pipeline.story_history.REPO_ROOT", tmp_path):
        # We need to copy fonts to tmp_path/assets/fonts so rendering doesn't fail
        fonts_src = Path(__file__).parent.parent.parent / "assets" / "fonts"
        fonts_dst = tmp_path / "assets" / "fonts"
        fonts_dst.mkdir(parents=True, exist_ok=True)
        for font_file in ["BebasNeue-Regular.ttf", "CreepsterCaps.ttf"]:
            if (fonts_src / font_file).is_file():
                shutil.copyfile(fonts_src / font_file, fonts_dst / font_file)

        code = run_script_main(run_slideshow, args)
        assert code == 0
        
        # Check that output video was generated in output/runs/
        runs_dir = tmp_path / "output" / "runs"
        assert runs_dir.exists()
        run_dirs = list(runs_dir.iterdir())
        assert len(run_dirs) > 0
        
        # Find the video file
        video_path = next(run_dirs[0].glob("**/short.mp4"))
        assert video_path.exists()
        assert video_path.stat().st_size > 0

@pytest.mark.tier1
def test_t1_f3_video_aspect_ratio(tmp_path):
    import scripts.run_slideshow as run_slideshow
    args = ["--channel", "football", "--image-urls", "http://example.com/1.jpg,http://example.com/2.jpg"]
    with patch("scripts.run_slideshow.REPO_ROOT", tmp_path), \
         patch("pipeline.story_history.REPO_ROOT", tmp_path):
        
        fonts_src = Path(__file__).parent.parent.parent / "assets" / "fonts"
        fonts_dst = tmp_path / "assets" / "fonts"
        fonts_dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fonts_src / "BebasNeue-Regular.ttf", fonts_dst / "BebasNeue-Regular.ttf")

        run_script_main(run_slideshow, args)
        video_path = next((tmp_path / "output" / "runs").glob("**/short.mp4"))
        
        props = get_media_properties(video_path)
        video_stream = next(s for s in props["streams"] if s["codec_type"] == "video")
        
        # Aspect ratio should be exactly vertical (e.g. 1080x1920)
        width = int(video_stream["width"])
        height = int(video_stream["height"])
        assert width == 1080
        assert height == 1920

@pytest.mark.tier1
def test_t1_f3_video_transitions(tmp_path):
    import scripts.run_short_ltx as run_short_ltx
    args = ["--channel", "fifa_2026", "--image-urls", "http://example.com/1.jpg,http://example.com/2.jpg"]
    with patch("scripts.run_short_ltx.REPO_ROOT", tmp_path), \
         patch("pipeline.story_history.REPO_ROOT", tmp_path):
        
        fonts_src = Path(__file__).parent.parent.parent / "assets" / "fonts"
        fonts_dst = tmp_path / "assets" / "fonts"
        fonts_dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fonts_src / "CreepsterCaps.ttf", fonts_dst / "CreepsterCaps.ttf")

        code = run_script_main(run_short_ltx, args)
        assert code == 0
        video_path = next((tmp_path / "output" / "runs").glob("**/short.mp4"))
        assert video_path.exists()

@pytest.mark.tier1
def test_t1_f3_video_codec(tmp_path):
    import scripts.run_slideshow as run_slideshow
    args = ["--channel", "football", "--image-urls", "http://example.com/1.jpg"]
    with patch("scripts.run_slideshow.REPO_ROOT", tmp_path), \
         patch("pipeline.story_history.REPO_ROOT", tmp_path):
        
        fonts_src = Path(__file__).parent.parent.parent / "assets" / "fonts"
        fonts_dst = tmp_path / "assets" / "fonts"
        fonts_dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fonts_src / "BebasNeue-Regular.ttf", fonts_dst / "BebasNeue-Regular.ttf")

        run_script_main(run_slideshow, args)
        video_path = next((tmp_path / "output" / "runs").glob("**/short.mp4"))
        
        props = get_media_properties(video_path)
        video_stream = next(s for s in props["streams"] if s["codec_type"] == "video")
        assert video_stream["codec_name"] == "h264"

@pytest.mark.tier1
def test_t1_f3_audio_track(tmp_path):
    import scripts.run_slideshow as run_slideshow
    args = ["--channel", "football", "--image-urls", "http://example.com/1.jpg"]
    with patch("scripts.run_slideshow.REPO_ROOT", tmp_path), \
         patch("pipeline.story_history.REPO_ROOT", tmp_path):
        
        fonts_src = Path(__file__).parent.parent.parent / "assets" / "fonts"
        fonts_dst = tmp_path / "assets" / "fonts"
        fonts_dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fonts_src / "BebasNeue-Regular.ttf", fonts_dst / "BebasNeue-Regular.ttf")

        run_script_main(run_slideshow, args)
        video_path = next((tmp_path / "output" / "runs").glob("**/short.mp4"))
        
        props = get_media_properties(video_path)
        audio_stream = next(s for s in props["streams"] if s["codec_type"] == "audio")
        assert audio_stream["codec_name"] == "aac"


@pytest.mark.tier2
def test_t2_f3_single_image(tmp_path):
    import scripts.run_slideshow as run_slideshow
    args = ["--channel", "football", "--image-urls", "http://example.com/1.jpg"]
    with patch("scripts.run_slideshow.REPO_ROOT", tmp_path), \
         patch("pipeline.story_history.REPO_ROOT", tmp_path):
        
        fonts_src = Path(__file__).parent.parent.parent / "assets" / "fonts"
        fonts_dst = tmp_path / "assets" / "fonts"
        fonts_dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fonts_src / "BebasNeue-Regular.ttf", fonts_dst / "BebasNeue-Regular.ttf")

        code = run_script_main(run_slideshow, args)
        assert code == 0
        video_path = next((tmp_path / "output" / "runs").glob("**/short.mp4"))
        assert video_path.exists()

@pytest.mark.tier2
def test_t2_f3_max_images(tmp_path):
    import scripts.run_slideshow as run_slideshow
    # Generate 50 images in list
    urls = ",".join([f"http://example.com/{i}.jpg" for i in range(50)])
    args = ["--channel", "football", "--image-urls", urls]
    with patch("scripts.run_slideshow.REPO_ROOT", tmp_path), \
         patch("pipeline.story_history.REPO_ROOT", tmp_path):
        
        fonts_src = Path(__file__).parent.parent.parent / "assets" / "fonts"
        fonts_dst = tmp_path / "assets" / "fonts"
        fonts_dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fonts_src / "BebasNeue-Regular.ttf", fonts_dst / "BebasNeue-Regular.ttf")

        code = run_script_main(run_slideshow, args)
        assert code == 0
        video_path = next((tmp_path / "output" / "runs").glob("**/short.mp4"))
        assert video_path.exists()

@pytest.mark.tier2
def test_t2_f3_size_mismatch(tmp_path):
    import scripts.run_slideshow as run_slideshow
    # Downloader returns the same size for mocks, but FFmpeg is forced to scale to 1080x1920.
    # We can test this by executing successfully (FFmpeg scales/crops and finishes without error).
    args = ["--channel", "football", "--image-urls", "http://example.com/1.jpg,http://example.com/2.jpg"]
    with patch("scripts.run_slideshow.REPO_ROOT", tmp_path), \
         patch("pipeline.story_history.REPO_ROOT", tmp_path):
        
        fonts_src = Path(__file__).parent.parent.parent / "assets" / "fonts"
        fonts_dst = tmp_path / "assets" / "fonts"
        fonts_dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fonts_src / "BebasNeue-Regular.ttf", fonts_dst / "BebasNeue-Regular.ttf")

        code = run_script_main(run_slideshow, args)
        assert code == 0
        video_path = next((tmp_path / "output" / "runs").glob("**/short.mp4"))
        assert video_path.exists()

@pytest.mark.tier2
def test_t2_f3_corrupted_image(tmp_path):
    import scripts.run_slideshow as run_slideshow
    # If an image on disk is corrupted, FFmpeg will fail.
    # Let's mock download_manual_images to return a path containing a corrupted file.
    corrupted_file = tmp_path / "corrupted_scene.jpg"
    corrupted_file.write_text("this is not an image", encoding="utf-8")
    
    args = ["--channel", "football", "--image-urls", "http://example.com/1.jpg"]
    with patch("scripts.run_slideshow.REPO_ROOT", tmp_path), \
         patch("pipeline.story_history.REPO_ROOT", tmp_path), \
         patch("scripts.run_slideshow.download_manual_images", return_value=[corrupted_file]):
        
        # Should raise an error because FFmpeg cannot process corrupted files
        with pytest.raises(Exception):
            run_script_main(run_slideshow, args)

@pytest.mark.tier2
def test_t2_f3_fps_override(tmp_path):
    import scripts.run_short_ltx as run_short_ltx
    # Verify that custom FPS or rendering runs successfully
    args = ["--channel", "fifa_2026", "--image-urls", "http://example.com/1.jpg"]
    with patch("scripts.run_short_ltx.REPO_ROOT", tmp_path), \
         patch("pipeline.story_history.REPO_ROOT", tmp_path), \
         patch("scripts.run_short_ltx.FPS", 30): # override default 24fps in LTX
        
        fonts_src = Path(__file__).parent.parent.parent / "assets" / "fonts"
        fonts_dst = tmp_path / "assets" / "fonts"
        fonts_dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fonts_src / "CreepsterCaps.ttf", fonts_dst / "CreepsterCaps.ttf")

        code = run_script_main(run_short_ltx, args)
        assert code == 0
        video_path = next((tmp_path / "output" / "runs").glob("**/short.mp4"))
        assert video_path.exists()
