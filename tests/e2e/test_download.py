import pytest
import urllib.request
from pathlib import Path
from pipeline.downloader import download_manual_images

@pytest.mark.tier1
def test_t1_f2_download_jpeg(tmp_path):
    res = download_manual_images("http://example.com/a.jpg,http://example.com/b.jpeg", tmp_path)
    assert len(res) == 2
    assert res[0].suffix in (".jpg", ".jpeg")
    assert res[1].suffix in (".jpg", ".jpeg")

@pytest.mark.tier1
def test_t1_f2_download_png(tmp_path):
    res = download_manual_images("http://example.com/a.png", tmp_path)
    assert len(res) == 1
    assert res[0].suffix == ".png"

@pytest.mark.tier1
def test_t1_f2_download_webp(tmp_path):
    res = download_manual_images("http://example.com/a.webp", tmp_path)
    assert len(res) == 1
    assert res[0].suffix == ".webp"

@pytest.mark.tier1
def test_t1_f2_download_mixed(tmp_path):
    res = download_manual_images("http://example.com/a.jpg,http://example.com/b.png,http://example.com/c.webp", tmp_path)
    assert len(res) == 3
    assert res[0].suffix in (".jpg", ".jpeg")
    assert res[1].suffix == ".png"
    assert res[2].suffix == ".webp"

@pytest.mark.tier1
def test_t1_f2_user_agent(tmp_path):
    # Execute a download and verify that the custom user agent is passed to urllib
    download_manual_images("http://example.com/ua_check.jpg", tmp_path)
    # Get the last call args
    call_args_list = urllib.request.urlopen.call_args_list
    assert len(call_args_list) > 0
    last_req = call_args_list[-1][0][0]
    # Check User-Agent header value
    user_agent = last_req.get_header("User-agent")
    assert "Mozilla" in user_agent or "Chrome" in user_agent


@pytest.mark.tier2
def test_t2_f2_http_404_error(tmp_path):
    with pytest.raises(RuntimeError) as excinfo:
        download_manual_images("http://fail_404.com/1.jpg", tmp_path)
    assert "404" in str(excinfo.value)

@pytest.mark.tier2
def test_t2_f2_http_403_error(tmp_path):
    with pytest.raises(RuntimeError) as excinfo:
        download_manual_images("http://fail_403.com/1.jpg", tmp_path)
    assert "403" in str(excinfo.value)

@pytest.mark.tier2
def test_t2_f2_magic_byte_fail(tmp_path):
    # html_content returns text/html, which lacks valid image magic bytes
    with pytest.raises(RuntimeError) as excinfo:
        download_manual_images("http://html_content.com/1.jpg", tmp_path)
    assert "magic bytes" in str(excinfo.value) or "HTML" in str(excinfo.value)

@pytest.mark.tier2
def test_t2_f2_download_timeout(tmp_path):
    with pytest.raises(RuntimeError) as excinfo:
        download_manual_images("http://timeout.com/1.jpg", tmp_path)
    assert "timeout" in str(excinfo.value)

@pytest.mark.tier2
def test_t2_f2_partial_download_fail(tmp_path):
    # First URL succeeds, second fails with 404. The whole execution should fail/raise error.
    with pytest.raises(RuntimeError) as excinfo:
        download_manual_images("http://example.com/ok.jpg,http://fail_404.com/bad.jpg", tmp_path)
    assert "404" in str(excinfo.value)
