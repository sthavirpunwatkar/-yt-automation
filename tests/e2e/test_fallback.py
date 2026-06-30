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

@pytest.mark.tier1
def test_t1_f4_no_urls_ltx(tmp_path):
    import scripts.run_short_ltx as run_short_ltx
    args = ["--channel", "fifa_2026"] # no --image-urls
    with patch("scripts.run_short_ltx.REPO_ROOT", tmp_path), \
         patch("pipeline.story_history.REPO_ROOT", tmp_path):
        fonts_src = Path(__file__).parent.parent.parent / "assets" / "fonts"
        fonts_dst = tmp_path / "assets" / "fonts"
        fonts_dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fonts_src / "CreepsterCaps.ttf", fonts_dst / "CreepsterCaps.ttf")

        code = run_script_main(run_short_ltx, args)
        assert code == 0

@pytest.mark.tier1
def test_t1_f4_no_urls_slideshow(tmp_path):
    import scripts.run_slideshow as run_slideshow
    args = ["--channel", "football"] # no --image-urls
    with patch("scripts.run_slideshow.REPO_ROOT", tmp_path), \
         patch("pipeline.story_history.REPO_ROOT", tmp_path):
        fonts_src = Path(__file__).parent.parent.parent / "assets" / "fonts"
        fonts_dst = tmp_path / "assets" / "fonts"
        fonts_dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fonts_src / "BebasNeue-Regular.ttf", fonts_dst / "BebasNeue-Regular.ttf")

        code = run_script_main(run_slideshow, args)
        assert code == 0

@pytest.mark.tier1
def test_t1_f4_download_fail_fallback(tmp_path):
    import scripts.run_short as run_short
    # This URL triggers 404 error during download, which should cause fallback to auto-generation
    args = ["--channel", "football", "--image-urls", "http://fail_404.com/1.jpg"]
    with patch("scripts.run_short.REPO_ROOT", tmp_path), \
         patch("pipeline.story_history.REPO_ROOT", tmp_path):
        fonts_src = Path(__file__).parent.parent.parent / "assets" / "fonts"
        fonts_dst = tmp_path / "assets" / "fonts"
        fonts_dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fonts_src / "BebasNeue-Regular.ttf", fonts_dst / "BebasNeue-Regular.ttf")

        code = run_script_main(run_short, args)
        assert code == 0

@pytest.mark.tier1
def test_t1_f4_workflow_empty_daily(tmp_path):
    import scripts.run_short_ltx as run_short_ltx
    args = ["--channel", "fifa_2026", "--image-urls", ""] # Empty input
    with patch("scripts.run_short_ltx.REPO_ROOT", tmp_path), \
         patch("pipeline.story_history.REPO_ROOT", tmp_path):
        fonts_src = Path(__file__).parent.parent.parent / "assets" / "fonts"
        fonts_dst = tmp_path / "assets" / "fonts"
        fonts_dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fonts_src / "CreepsterCaps.ttf", fonts_dst / "CreepsterCaps.ttf")

        code = run_script_main(run_short_ltx, args)
        assert code == 0

@pytest.mark.tier1
def test_t1_f4_workflow_empty_slideshow(tmp_path):
    import scripts.run_slideshow as run_slideshow
    args = ["--channel", "football", "--image-urls", ""] # Empty input
    with patch("scripts.run_slideshow.REPO_ROOT", tmp_path), \
         patch("pipeline.story_history.REPO_ROOT", tmp_path):
        fonts_src = Path(__file__).parent.parent.parent / "assets" / "fonts"
        fonts_dst = tmp_path / "assets" / "fonts"
        fonts_dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fonts_src / "BebasNeue-Regular.ttf", fonts_dst / "BebasNeue-Regular.ttf")

        code = run_script_main(run_slideshow, args)
        assert code == 0


@pytest.mark.tier2
def test_t2_f4_all_downloads_fail(tmp_path):
    import scripts.run_short as run_short
    # This URL triggers 403 forbidden error, fallback to auto
    args = ["--channel", "football", "--image-urls", "http://fail_403.com/1.jpg"]
    with patch("scripts.run_short.REPO_ROOT", tmp_path), \
         patch("pipeline.story_history.REPO_ROOT", tmp_path):
        fonts_src = Path(__file__).parent.parent.parent / "assets" / "fonts"
        fonts_dst = tmp_path / "assets" / "fonts"
        fonts_dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fonts_src / "BebasNeue-Regular.ttf", fonts_dst / "BebasNeue-Regular.ttf")

        code = run_script_main(run_short, args)
        assert code == 0

@pytest.mark.tier2
def test_t2_f4_partial_download_fallback(tmp_path):
    import scripts.run_short as run_short
    # One ok URL, one failing URL. The partial failure triggers fallback to auto.
    args = ["--channel", "football", "--image-urls", "http://example.com/ok.jpg,http://fail_404.com/bad.jpg"]
    with patch("scripts.run_short.REPO_ROOT", tmp_path), \
         patch("pipeline.story_history.REPO_ROOT", tmp_path):
        fonts_src = Path(__file__).parent.parent.parent / "assets" / "fonts"
        fonts_dst = tmp_path / "assets" / "fonts"
        fonts_dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fonts_src / "BebasNeue-Regular.ttf", fonts_dst / "BebasNeue-Regular.ttf")

        code = run_script_main(run_short, args)
        assert code == 0

@pytest.mark.tier2
def test_t2_f4_empty_fallback_queries(tmp_path):
    import scripts.run_slideshow as run_slideshow
    args = ["--channel", "football", "--image-urls", "http://fail_404.com/bad.jpg"]
    
    # Mock Groq to return empty search queries, fallback should handle empty list or fail gracefully
    def empty_groq(*args, **kwargs):
        return {
            "youtube_title": "Title",
            "youtube_description": "Desc",
            "full_narration": "Narration.",
            "image_prompts": [],
            "visual_search_queries": []
        }

    with patch("scripts.run_slideshow.REPO_ROOT", tmp_path), \
         patch("pipeline.story_history.REPO_ROOT", tmp_path), \
         patch("scripts.run_slideshow.generate_short_pack", side_effect=empty_groq):
        
        fonts_src = Path(__file__).parent.parent.parent / "assets" / "fonts"
        fonts_dst = tmp_path / "assets" / "fonts"
        fonts_dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fonts_src / "BebasNeue-Regular.ttf", fonts_dst / "BebasNeue-Regular.ttf")

        # Because fallback queries are empty, the slideshow run has no images to fetch and should exit with error 1
        code = run_script_main(run_slideshow, args)
        assert code == 1

@pytest.mark.tier2
def test_t2_f4_zero_results_fallback(tmp_path):
    import scripts.run_slideshow as run_slideshow
    args = ["--channel", "football", "--image-urls", "http://fail_404.com/bad.jpg"]
    
    # Mock DDG fetch to return failure (zero results)
    def zero_results_fetch(*args, **kwargs):
        return "fail", "Zero results found"

    with patch("scripts.run_slideshow.REPO_ROOT", tmp_path), \
         patch("pipeline.story_history.REPO_ROOT", tmp_path), \
         patch("scripts.run_slideshow.fetch_web_image", side_effect=zero_results_fetch):
        
        fonts_src = Path(__file__).parent.parent.parent / "assets" / "fonts"
        fonts_dst = tmp_path / "assets" / "fonts"
        fonts_dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fonts_src / "BebasNeue-Regular.ttf", fonts_dst / "BebasNeue-Regular.ttf")

        # Fallback occurs but fetches zero results, should exit with error 1
        code = run_script_main(run_slideshow, args)
        assert code == 1

@pytest.mark.tier2
def test_t2_f4_successful_fallback_render(tmp_path):
    import scripts.run_slideshow as run_slideshow
    args = ["--channel", "football", "--image-urls", "http://fail_404.com/bad.jpg"]
    with patch("scripts.run_slideshow.REPO_ROOT", tmp_path), \
         patch("pipeline.story_history.REPO_ROOT", tmp_path):
        
        fonts_src = Path(__file__).parent.parent.parent / "assets" / "fonts"
        fonts_dst = tmp_path / "assets" / "fonts"
        fonts_dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(fonts_src / "BebasNeue-Regular.ttf", fonts_dst / "BebasNeue-Regular.ttf")

        # Fails download, falls back to web images, renders successfully
        code = run_script_main(run_slideshow, args)
        assert code == 0
        video_path = next((tmp_path / "output" / "runs").glob("**/short.mp4"))
        assert video_path.exists()
