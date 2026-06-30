"""Image fetching via DuckDuckGo Image Search."""
from __future__ import annotations

import os
import random
import time
from pathlib import Path

import httpx
from ddgs import DDGS

STYLE_SUFFIX = " high quality photograph"
DEFAULT_NEGATIVE = ""

def full_visual_prompt(scene: str, style_suffix: str | None = None) -> str:
    """Return the raw search query without appending AI style suffixes, but append site exclusions to avoid watermarks."""
    exclusions = "-site:gettyimages.com -site:alamy.com -site:shutterstock.com -site:istockphoto.com"
    return f"{scene.strip()} {exclusions}"


def _search_and_download(prompt: str) -> bytes:
    """Search DDG for images and download the first successful one."""
    print(f"      DDG Search: {prompt}")
    try:
        with DDGS() as ddgs:
            # We request a few results so we can fallback if a URL is broken
            results = list(ddgs.images(
                prompt,
                safesearch="moderate",
                size="Large",
                max_results=5,
            ))
    except Exception as e:
        raise RuntimeError(f"DDG Search failed: {e}")

    if not results:
        raise RuntimeError(f"No image results found for: {prompt}")

    with httpx.Client(timeout=15.0, follow_redirects=True) as client:
        for res in results:
            img_url = res.get("image")
            if not img_url:
                continue
            try:
                # Add a browser-like User-Agent to avoid 403s
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
                }
                resp = client.get(img_url, headers=headers)
                resp.raise_for_status()
                # Verify it's actually an image
                content_type = resp.headers.get("Content-Type", "")
                if "text/html" in content_type:
                    continue
                print(f"      Downloaded: {img_url}")
                return resp.content
            except Exception as e:
                print(f"      Failed to download {img_url}: {e}")
                continue

    raise RuntimeError(f"Failed to download any images for: {prompt}")


def save_scene_image(
    index: int,
    prompt: str,
    out_path: Path,
    *,
    width: int = 768,
    height: int = 768,
    negative: str = DEFAULT_NEGATIVE,
) -> tuple[str, str]:
    """Fetch and save one image from the internet. Returns (status, detail)."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        img_bytes = _search_and_download(prompt)
        out_path.write_bytes(img_bytes)
        
        # Strip watermarks and text automatically
        detail = "internet_search"
        try:
            from pipeline.watermark_removal import remove_watermark
            remove_watermark(str(out_path), str(out_path))
            detail = "internet_search (watermark removed)"
        except ImportError:
            pass # easyocr not installed
        except Exception as wm_e:
            print(f"      [warn] Watermark removal failed: {wm_e}")
            
        return "ok", detail
    except Exception as e:
        return "fail", str(e)
