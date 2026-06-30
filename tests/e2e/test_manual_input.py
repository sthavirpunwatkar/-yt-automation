import os
import json
import pytest
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

@pytest.mark.tier1
def test_t1_f1_cli_urls_ltx():
    import scripts.run_short_ltx as run_short_ltx
    args = ["--channel", "fifa_2026", "--image-urls", "http://example.com/1.jpg,http://example.com/2.jpg"]
    # We expect a success run (exit code 0 or SystemExit with 0)
    code = run_script_main(run_short_ltx, args)
    assert code == 0

@pytest.mark.tier1
def test_t1_f1_cli_urls_slideshow():
    import scripts.run_slideshow as run_slideshow
    args = ["--channel", "fifa_2026", "--image-urls", "http://example.com/1.jpg,http://example.com/2.jpg"]
    code = run_script_main(run_slideshow, args)
    assert code == 0

@pytest.mark.tier1
def test_t1_f1_file_urls(tmp_path):
    import scripts.run_short as run_short
    url_file = tmp_path / "urls.txt"
    url_file.write_text("http://example.com/1.jpg\nhttp://example.com/2.jpg", encoding="utf-8")
    args = ["--channel", "football", "--image-urls", str(url_file)]
    code = run_script_main(run_short, args)
    assert code == 0

@pytest.mark.tier1
def test_t1_f1_env_urls():
    import scripts.run_short as run_short
    with patch.dict(os.environ, {"IMAGE_URLS": "http://example.com/1.jpg,http://example.com/2.jpg"}):
        args = ["--channel", "football"]
        code = run_script_main(run_short, args)
        assert code == 0

@pytest.mark.tier1
def test_t1_f1_json_urls():
    import scripts.run_short as run_short
    json_str = json.dumps(["http://example.com/1.jpg", "http://example.com/2.jpg"])
    args = ["--channel", "football", "--image-urls", json_str]
    code = run_script_main(run_short, args)
    assert code == 0


@pytest.mark.tier2
def test_t2_f1_empty_urls_input():
    import scripts.run_short as run_short
    # When empty, it falls back to auto-generation which is mocked to succeed
    args = ["--channel", "football", "--image-urls", ""]
    code = run_script_main(run_short, args)
    assert code == 0

@pytest.mark.tier2
def test_t2_f1_urls_whitespace():
    import scripts.run_short as run_short
    args = ["--channel", "football", "--image-urls", "  http://example.com/1.jpg  ,   http://example.com/2.jpg  "]
    code = run_script_main(run_short, args)
    assert code == 0

@pytest.mark.tier2
def test_t2_f1_large_url_list():
    import scripts.run_short as run_short
    # Boundary: large URL list (e.g. 50 URLs)
    urls = ",".join([f"http://example.com/{i}.jpg" for i in range(50)])
    args = ["--channel", "football", "--image-urls", urls]
    code = run_script_main(run_short, args)
    assert code == 0

@pytest.mark.tier2
def test_t2_f1_malformed_urls(tmp_path):
    from pipeline.downloader import download_manual_images
    with pytest.raises(Exception) as excinfo:
        download_manual_images("example.com/1.jpg", tmp_path)
    assert "Invalid URL structure" in str(excinfo.value) or "Failed to download manual image" in str(excinfo.value)

@pytest.mark.tier2
def test_t2_f1_duplicate_urls():
    import scripts.run_short as run_short
    args = ["--channel", "football", "--image-urls", "http://example.com/1.jpg,http://example.com/1.jpg"]
    code = run_script_main(run_short, args)
    assert code == 0
