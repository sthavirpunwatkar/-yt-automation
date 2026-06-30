"""Manual image downloader helper using standard urllib."""
from __future__ import annotations

import urllib.request
import urllib.parse
import shutil
from pathlib import Path

def download_manual_images(urls_str: str, dest_dir: Path) -> list[Path]:
    """
    Parses a comma-separated list of image URLs, downloads them to dest_dir,
    and returns a list of local Path objects.
    
    Args:
        urls_str: Comma-separated string of URLs (e.g., "http://example.com/a.jpg, http://example.com/b.png")
        dest_dir: The directory where downloaded images should be saved.
    
    Returns:
        List of Paths to the successfully downloaded local image files.
    """
    if not urls_str or not urls_str.strip():
        return []
        
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    # If the input is a valid file path, read the URLs from the file
    try:
        potential_file = Path(urls_str.strip())
        if potential_file.is_file():
            urls_str = potential_file.read_text(encoding="utf-8")
    except Exception:
        pass

    urls_str_stripped = urls_str.strip()
    urls = []
    
    # Try parsing as JSON list/dict if it looks like one
    if urls_str_stripped.startswith("[") or urls_str_stripped.startswith("{"):
        import json
        try:
            parsed = json.loads(urls_str_stripped)
            if isinstance(parsed, list):
                urls = [str(u).strip() for u in parsed if str(u).strip()]
            elif isinstance(parsed, dict):
                urls = [str(v).strip() for v in parsed.values() if str(v).strip()]
        except Exception:
            pass

    # If not parsed as JSON, split by comma/newline
    if not urls:
        for line in urls_str.replace("\n", ",").split(","):
            cleaned = line.strip()
            if cleaned:
                urls.append(cleaned)
    downloaded_paths: list[Path] = []
    
    # Standard headers to prevent bot-detection blocks (403)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    for idx, url in enumerate(urls, 1):
        try:
            parsed_url = urllib.parse.urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError(f"Invalid URL structure: {url}")
                
            # Determine extension
            path_suffix = Path(parsed_url.path).suffix.lower()
            if path_suffix not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
                path_suffix = ".jpg"  # Default fallback
                
            out_path = dest_dir / f"manual_img_{idx:02d}{path_suffix}"
            
            print(f"Downloading manual image {idx}/{len(urls)}: {url}")
            req = urllib.request.Request(url, headers=headers)
            
            # 15s timeout to prevent infinite hanging
            with urllib.request.urlopen(req, timeout=15) as response:
                content_type = response.headers.get("Content-Type", "")
                if content_type and "image" not in content_type.lower():
                    print(f"   [Warning] Response content-type '{content_type}' might not be an image.")
                
                data = response.read()
                
                # Check magic bytes: JPEG, PNG, GIF, WEBP
                is_valid_image = (
                    data.startswith(b'\xff\xd8\xff') or 
                    data.startswith(b'\x89PNG\r\n\x1a\n') or 
                    data.startswith(b'GIF8') or 
                    (data.startswith(b'RIFF') and b'WEBP' in data[8:12])
                )
                if not is_valid_image:
                    raise ValueError("Downloaded data lacks valid image magic bytes (likely HTML or corrupted).")
                    
                out_path.write_bytes(data)
                    
            if not out_path.exists() or out_path.stat().st_size == 0:
                raise RuntimeError("Downloaded file is empty or missing.")
                
            downloaded_paths.append(out_path)
            print(f"   Successfully downloaded to {out_path} ({out_path.stat().st_size} bytes)")
            
        except Exception as e:
            print(f"   [Error] Failed downloading {url}: {e}")
            raise RuntimeError(f"Failed to download manual image at index {idx} ({url}): {e}") from e
            
    return downloaded_paths
