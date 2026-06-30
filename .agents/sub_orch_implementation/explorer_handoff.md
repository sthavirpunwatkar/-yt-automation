# Investigation Report: Implementation Strategy for Manually Provided Image URLs

## 1. Observation

### Script 1: `scripts/run_short.py`
In `scripts/run_short.py`, images are generated/fetched via DeAPI and saved in `img_dir` under a sequential naming scheme (`scene_01.png`, `scene_02.png`, etc.) in lines 211-223:
```python
211:     print(f"③ Images: {len(image_prompts)} scenes ({cooldown}s cooldown)…")
212:     image_paths: list[Path] = []
213:     for i, ip in enumerate(image_prompts):
214:         prompt = full_visual_prompt(ip, style_suffix=style_suffix)
215:         out = img_dir / f"scene_{i + 1:02d}.png"
216:         st, detail = save_scene_image(i + 1, prompt, out, width=w, height=h, negative=negative)
217:         if st != "ok":
218:             raise RuntimeError(f"Image {i + 1} failed: {detail}")
219:         print(f"   scene {i + 1}/{len(image_prompts)}: {detail}")
220:         image_paths.append(out)
221:         if i < len(image_prompts) - 1:
222:             time.sleep(cooldown)
```

### Script 2: `scripts/run_short_ltx.py`
In `scripts/run_short_ltx.py`, video clips are fetched/generated via DeAPI's `txt2video` API in lines 394-417:
```python
394:     # 4. Generate 8 Videos via DeAPI txt2video
395:     cooldown = 10
396:     print(f"\n④ DeAPI Video Generation: 8 clips ({cooldown}s cooldown between submissions)...")
397:     raw_video_paths = []
398:     
399:     with httpx.Client(timeout=120.0) as client:
400:         for i, prompt in enumerate(video_prompts, 1):
401:             full_prompt = prompt + (preset.get("image_style_suffix") or "")
402:             print(f"   [Clip {i}/8] Submitting prompt: {full_prompt[:80]}...")
403:             
404:             request_id, successful_token = submit_video(full_prompt, client)
405:             print(f"      Job ID: {request_id}")
406:             
407:             video_bytes = poll_video(request_id, successful_token, client)
408:             
409:             clip_path = vid_dir / f"raw_clip_{i:02d}.mp4"
410:             clip_path.write_bytes(video_bytes)
411:             print(f"      Saved raw clip to: {clip_path} ({len(video_bytes)//1024}KB)")
412:             raw_video_paths.append(clip_path)
```
These raw video clips are later scaled, cropped, and set to target durations via `preprocess_clip` in lines 418-428:
```python
418:     # 5. Pre-process and time-scale clips
419:     print("\n⑤ Pre-processing clips (scaling, cropping to 1080x1920, and adjusting speed)...")
420:     clip_dur = (total_dur + 7 * FADE_DUR) / 8
421:     print(f"   Target duration per clip: {clip_dur:.2f}s")
422:     
423:     processed_video_paths = []
424:     for i, raw_path in enumerate(raw_video_paths, 1):
425:         proc_path = tmp_dir / f"clip_{i:02d}.mp4"
426:         preprocess_clip(raw_path, proc_path, clip_dur)
427:         processed_video_paths.append(proc_path)
428:         print(f"   Processed clip {i}/8")
```

### Script 3: `scripts/run_slideshow.py`
In `scripts/run_slideshow.py`, images are fetched using a DuckDuckGo search query via the `fetch_web_image` helper inside lines 103-124:
```python
103:     # 4. Fetch Images
104:     print(f"\n④ Fetching {len(search_queries)} web images...")
105:     image_paths = []
106:     
107:     for i, query in enumerate(search_queries, 1):
108:         # Force strict football context so DuckDuckGo doesn't return vague/generic images
109:         strict_query = f"{query} FIFA World Cup football match"
110:         print(f"   [Image {i}/{len(search_queries)}] Searching: {strict_query}")
111:         out_path = img_dir / f"img_{i:02d}.jpg"
112:         status, detail = fetch_web_image(strict_query, out_path)
113:         if status == "ok":
114:             print(f"      Saved: {detail}")
115:             image_paths.append(out_path)
```

### Workflow 1: `.github/workflows/daily_short.yml`
Currently accepts `channel` and `topic` as workflow inputs (lines 9-18) and executes `scripts/run_short_ltx.py` (lines 66-74):
```yaml
9:     inputs:
10:       channel:
11:         description: "Channel preset (fifa_2026 or football)"
12:         required: false
13:         default: "fifa_2026"
14:       topic:
15:         description: "Optional topic override (leave empty for auto-selection)"
16:         required: false
17:         default: ""
...
66:       - name: Generate & upload Short
67:         run: |
68:           CHANNEL="${{ github.event.inputs.channel || 'fifa_2026' }}"
69:           TOPIC="${{ github.event.inputs.topic || '' }}"
70:           if [ -n "$TOPIC" ]; then
71:             python -u scripts/run_short_ltx.py --channel "$CHANNEL" --topic "$TOPIC" --upload --privacy private
72:           else
73:             python -u scripts/run_short_ltx.py --channel "$CHANNEL" --upload --privacy private
74:           fi
```

### Workflow 2: `.github/workflows/slideshow.yml`
Currently accepts `channel` and `topic` as workflow inputs (lines 10-20) and executes `scripts/run_slideshow.py` (lines 46-54):
```yaml
10:   workflow_dispatch:
11:     inputs:
12:       channel:
13:         description: "Channel preset (fifa_2026 or football)"
14:         required: false
15:         default: "fifa_2026"
16:       topic:
17:         description: "Optional topic override (leave empty for auto-selection)"
18:         required: false
19:         default: ""
...
46:       - name: Run Slideshow Engine
47:         run: |
48:           CHANNEL="${{ github.event.inputs.channel || 'fifa_2026' }}"
49:           TOPIC="${{ github.event.inputs.topic || '' }}"
50:           if [ -n "$TOPIC" ]; then
51:             python scripts/run_slideshow.py --channel "$CHANNEL" --topic "$TOPIC" --upload --privacy public
52:           else
53:             python scripts/run_slideshow.py --channel "$CHANNEL" --upload --privacy public
54:           fi
```


## 2. Logic Chain

1. **Manual Execution Parameter**: By introducing a CLI argument `--image-urls` to all three scripts, users can manually pass a comma-separated list of image URLs.
2. **Download Handling**: If this argument is set, the scripts can skip the automated image generation (DeAPI/Web search) and instead invoke a Python downloader function to fetch images locally using standard libraries.
3. **Mismatched Image Pacing**:
   - In `run_short.py` and `run_slideshow.py`, the images are sent to `render_vertical_short()`. This function scales the crossfade transitions and clip durations dynamically based on the length of `image_paths`. Thus, the slideshow adjusts natively to the number of downloaded manual images without modifications to the rendering engine.
   - In `run_short_ltx.py`, the pipeline expects `.mp4` video clips. However, we can satisfy this requirement by generating video clips from static images via FFmpeg. We can calculate the exact target duration per segment `clip_dur` based on the number of manual images, and convert each image to an `.mp4` clip using the `-loop 1` option. By scaling and cropping them to `1080x1920` at 30 fps during this stage, these clips can bypass the preprocessing stage and be stitched together by the existing `render_video_ltx()` function with zero changes to the rendering pipeline.
4. **GitHub Actions Integration**: By extending the `workflow_dispatch` input schema to accept a new `image_urls` input, GitHub Actions can pass this string down to the Python scripts during execution.


## 3. Caveats

* **Image Validation**: The downloader relies on parsing file extensions and HTTP `Content-Type` headers. If URLs do not return standard image content (e.g. they return HTML error pages or redirect to login portals), the script will raise a `RuntimeError` to prevent pipeline failures in the downstream rendering steps.
* **Aspect Ratio Distortions**: While FFmpeg's `force_original_aspect_ratio=increase` handles scaling and cropping to a 9:16 layout without stretching the image, landscape images might lose significant detail on their horizontal edges.
* **TTS Alignment**: The number of images provided manually might differ from the visual scene markers generated by Groq. The audio/timing script handles captions based on sentence timings, but the visual progression will transition based on the count of provided images, which may lead to semantic misalignment between narration and visuals if the manual image order/count doesn't correspond to the generated story structure.


## 4. Conclusion & Implementation Strategy

### A. Python Image Downloader Function (`pipeline/downloader.py` or `pipeline/images.py`)
This function parses, filters, and downloads manual URLs using `urllib.request` and sets a browser-like User-Agent to bypass standard bot checks:

```python
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
        
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    # Split, clean, and filter empty strings
    urls = [u.strip() for u in urls_str.split(",") if u.strip()]
    downloaded_paths = []
    
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
                    
                with open(out_path, "wb") as f:
                    shutil.copyfileobj(response, f)
                    
            if not out_path.exists() or out_path.stat().st_size == 0:
                raise RuntimeError("Downloaded file is empty or missing.")
                
            downloaded_paths.append(out_path)
            print(f"   Successfully downloaded to {out_path} ({out_path.stat().st_size} bytes)")
            
        except Exception as e:
            print(f"   [Error] Failed downloading {url}: {e}")
            raise RuntimeError(f"Failed to download manual image at index {idx} ({url}): {e}") from e
            
    return downloaded_paths
```

---

### B. Handling Static Images in `run_short_ltx.py`
To process static images in the LTX text-to-video pipeline, we convert the static images into short video clips using an FFmpeg subprocess. 
We can insert a new helper function `convert_image_to_video_clip` and update the workflow to bypass DeAPI generation when `--image-urls` is present.

#### Conversion Helper
```python
def convert_image_to_video_clip(img_path: Path, out_video_path: Path, duration: float) -> None:
    """
    Converts a static image to a 1080x1920 video clip of the specified duration
    at 30fps using FFmpeg.
    """
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "fps=30"
    )
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-loop", "1",
        "-i", str(img_path),
        "-t", f"{duration:.4f}",
        "-vf", vf,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        str(out_video_path)
    ]
    subprocess.run(cmd, check=True)
```

#### Pipeline Logic Integration (Step 4 & 5 Replacement in `run_short_ltx.py`)
```python
    if args.image_urls:
        print(f"\n④ Manual Mode: Downloading {args.image_urls.count(',') + 1} manual images...")
        image_paths = download_manual_images(args.image_urls, vid_dir)
        
        n_clips = len(image_paths)
        clip_dur = (total_dur + (n_clips - 1) * FADE_DUR) / n_clips if n_clips > 1 else total_dur
        print(f"\n⑤ Converting manual images to video clips (duration={clip_dur:.2f}s)...")
        
        processed_video_paths = []
        for i, img_path in enumerate(image_paths, 1):
            proc_path = tmp_dir / f"clip_{i:02d}.mp4"
            convert_image_to_video_clip(img_path, proc_path, clip_dur)
            processed_video_paths.append(proc_path)
            print(f"   Converted manual image {i}/{n_clips} -> {proc_path}")
    else:
        # Original DeAPI and Preprocessing pipeline
        # (Submit video, poll status, download bytes, preprocess_clip, etc.)
        ...
```

---

### C. GitHub Actions Configuration Changes

#### 1. `.github/workflows/daily_short.yml`
Expose the new input and append it to the argument list:
```yaml
# Add to workflow inputs (around line 18)
      image_urls:
        description: "Comma-separated list of manual image URLs (forces static image slideshow)"
        required: false
        default: ""
```
Update the generate step (lines 66-74):
```yaml
      - name: Generate & upload Short
        run: |
          CHANNEL="${{ github.event.inputs.channel || 'fifa_2026' }}"
          TOPIC="${{ github.event.inputs.topic || '' }}"
          IMAGE_URLS="${{ github.event.inputs.image_urls || '' }}"
          
          ARGS=(--channel "$CHANNEL" --upload --privacy private)
          if [ -n "$TOPIC" ]; then
            ARGS+=(--topic "$TOPIC")
          fi
          if [ -n "$IMAGE_URLS" ]; then
            ARGS+=(--image-urls "$IMAGE_URLS")
          fi
          
          python -u scripts/run_short_ltx.py "${ARGS[@]}"
```

#### 2. `.github/workflows/slideshow.yml`
Expose the new input and append it to the argument list:
```yaml
# Add to workflow inputs (around line 20)
      image_urls:
        description: "Comma-separated list of manual image URLs (bypasses DuckDuckGo search)"
        required: false
        default: ""
```
Update the run step (lines 46-54):
```yaml
      - name: Run Slideshow Engine
        run: |
          CHANNEL="${{ github.event.inputs.channel || 'fifa_2026' }}"
          TOPIC="${{ github.event.inputs.topic || '' }}"
          IMAGE_URLS="${{ github.event.inputs.image_urls || '' }}"
          
          ARGS=(--channel "$CHANNEL" --upload --privacy public)
          if [ -n "$TOPIC" ]; then
            ARGS+=(--topic "$TOPIC")
          fi
          if [ -n "$IMAGE_URLS" ]; then
            ARGS+=(--image-urls "$IMAGE_URLS")
          fi
          
          python scripts/run_slideshow.py "${ARGS[@]}"
```


## 5. Verification Method

1. **Local Script Dry-Run**: Run the modified scripts locally bypassing YouTube upload to verify local rendering output:
   ```bash
   # Test run_short.py with manual URLs
   python scripts/run_short.py --channel fifa_2026 --image-urls "https://picsum.photos/1080/1920,https://picsum.photos/1080/1920"
   
   # Test run_short_ltx.py with manual URLs
   python scripts/run_short_ltx.py --channel fifa_2026 --image-urls "https://picsum.photos/1080/1920,https://picsum.photos/1080/1920"
   
   # Test run_slideshow.py with manual URLs
   python scripts/run_slideshow.py --channel fifa_2026 --image-urls "https://picsum.photos/1080/1920,https://picsum.photos/1080/1920"
   ```
2. **Result Inspection**:
   - Verify that the downloaded images are correctly placed under `output/runs/<run_name>/images/` (or `videos/` for LTX) and named sequentially.
   - For LTX, check the contents of `tmp_dir` before cleanup (or comment out `shutil.rmtree(tmp_dir)` during local tests) to confirm `clip_01.mp4` and `clip_02.mp4` have been successfully rendered, have 1080x1920 aspect ratios, and match `clip_dur` in length.
   - Open the resulting `short.mp4` to inspect transitions, crossfades, and caption timings.
3. **Invalidation Conditions**:
   - If `ffmpeg` fails during the static-image-to-video phase due to format incompatibility (e.g. if a URL yields a webp file with transparency and requires extra filters), the pipeline will break.
   - If URLs list contains spaces around commas or trailing commas, the splits should handle them gracefully without throwing HTTP parse errors.
