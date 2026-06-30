import os
import pytest
import shutil
from pathlib import Path
from unittest.mock import patch

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

@pytest.mark.tier4
def test_t4_e2e_manual_ltx(tmp_path):
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
        assert video_path.stat().st_size > 0

@pytest.mark.tier4
def test_t4_e2e_manual_slideshow(tmp_path):
    import scripts.run_slideshow as run_slideshow
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
        assert video_path.stat().st_size > 0

@pytest.mark.tier4
def test_t4_workflow_daily_short(tmp_path):
    # Simulates: python -u scripts/run_short_ltx.py --channel fifa_2026 --upload --privacy private --image-urls ...
    import scripts.run_short_ltx as run_short_ltx
    args = ["--channel", "fifa_2026", "--upload", "--privacy", "private", "--image-urls", "http://example.com/1.jpg,http://example.com/2.jpg"]
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

@pytest.mark.tier4
def test_t4_workflow_slideshow(tmp_path):
    # Simulates: python scripts/run_slideshow.py --channel football --upload --privacy public --image-urls ...
    import scripts.run_slideshow as run_slideshow
    args = ["--channel", "football", "--upload", "--privacy", "public", "--image-urls", "http://example.com/1.jpg,http://example.com/2.jpg"]
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

@pytest.mark.tier4
def test_t4_fifa_scrape_fallback(tmp_path):
    import scripts.fifa_orchestrator as fifa_orchestrator
    
    # We patch search_fifa_video to raise an Exception, triggering graceful fallback
    # We set environment variables to pass manual URLs to the fallback slideshow engine
    with patch("scripts.fifa_orchestrator.search_fifa_video", side_effect=RuntimeError("Scraping blocked")), \
         patch("scripts.fifa_orchestrator.REPO_ROOT", tmp_path), \
         patch("scripts.run_slideshow.REPO_ROOT", tmp_path), \
         patch("pipeline.story_history.REPO_ROOT", tmp_path), \
         patch.dict(os.environ, {"IMAGE_URLS": "http://example.com/1.jpg,http://example.com/2.jpg"}):
        
        fonts_src = Path(__file__).parent.parent.parent / "assets" / "fonts"
        fonts_dst = tmp_path / "assets" / "fonts"
        fonts_dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fonts_src / "BebasNeue-Regular.ttf", fonts_dst / "BebasNeue-Regular.ttf")

        # Run fifa_orchestrator.py main block inside our patch
        original_argv = list(os.sys.argv)
        os.sys.argv = ["fifa_orchestrator.py"]
        try:
            # Recreate main logic
            url = fifa_orchestrator.search_fifa_video()
            fifa_orchestrator.generate_shorts(url)
            fifa_orchestrator.process_and_upload_shorts()
            code = 0
        except Exception as e:
            # Graceful fallback logic
            print(f"Video scraping failed: {e}")
            os.sys.argv = ["fifa_orchestrator.py", "--upload"]
            try:
                import scripts.run_slideshow as run_slideshow
                run_slideshow.main()
                code = 0
            except Exception as fallback_err:
                code = 1
                
        assert code == 0
        video_path = next((tmp_path / "output" / "runs").glob("**/short.mp4"))
        assert video_path.exists()
