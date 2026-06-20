import os
from pathlib import Path
from ddgs import DDGS
import httpx

def fetch_web_image(query: str, out_path: str | Path) -> tuple[str, str]:
    """
    Fetches the first high-quality image for the given query using DuckDuckGo.
    Saves it to out_path.
    Returns ('ok', url) on success, ('fail', reason) on failure.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # We append ' hd high quality' to get better results
        search_query = f"{query} hd high resolution"
        
        with DDGS() as ddgs:
            # We search for images, safely. 
            # If we wanted purely safe for reuse, there is currently no direct DDG param in the lib, 
            # so we rely on fair use for Option A.
            results = ddgs.images(
                search_query,
                safesearch="moderate",
                size="Large",
                max_results=5,
            )
            
            if not results:
                return "fail", "No images found."
            
            # Try to download the first working image
            for result in results:
                image_url = result.get("image")
                if not image_url:
                    continue
                    
                # Ensure it's a typical image format
                lower_url = image_url.lower()
                if not (lower_url.endswith(".jpg") or lower_url.endswith(".jpeg") or lower_url.endswith(".png")):
                    continue
                    
                try:
                    with httpx.Client(timeout=15.0) as client:
                        resp = client.get(image_url)
                        resp.raise_for_status()
                        
                        # Verify it's actually an image by checking magic bytes
                        content = resp.content
                        if not (content.startswith(b'\xff\xd8\xff') or content.startswith(b'\x89PNG\r\n\x1a\n') or content.startswith(b'RIFF')):
                            print(f"      [WebImages] Invalid image data (likely HTML) from {image_url}")
                            continue
                            
                        out_path.write_bytes(content)
                        return "ok", image_url
                except Exception as dl_err:
                    print(f"      [WebImages] Failed to download {image_url}: {dl_err}")
                    continue
            
            return "fail", "All found images failed to download."

    except Exception as e:
        return "fail", str(e)

if __name__ == "__main__":
    # Test script
    print("Testing DuckDuckGo Image Fetcher...")
    status, detail = fetch_web_image("Kylian Mbappe goal celebration match", "output/test_mbappe.jpg")
    print(f"Status: {status}, Detail: {detail}")
