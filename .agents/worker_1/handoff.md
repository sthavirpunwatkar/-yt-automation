# Handoff Report: Manual Image URL Downloading & Processing Implementation

## 1. Observation
- Implemented `pipeline/downloader.py` which contains `download_manual_images(urls_str: str, dest_dir: Path) -> list[Path]`. It parses a comma-separated list of image URLs, cleans and validates them, downloads using `urllib.request` with standard `User-Agent` headers to bypass basic bot prevention blocks, and returns a list of local file `Path` objects.
- Modified `scripts/run_short.py` to:
  - Add `--image-urls` CLI argument.
  - Wrap `download_manual_images` in a `try...except` block, downloading images to `img_dir`. If it fails, print a fallback warning and fall back to DeAPI generation. Bypasses DeAPI generation if the download is successful.
- Modified `scripts/run_short_ltx.py` to:
  - Add `--image-urls` CLI argument.
  - Wrap `download_manual_images` in a `try...except` block, downloading to `vid_dir`. If it fails, fall back to DeAPI.
  - If successful, bypass DeAPI `txt2video` generation/polling and preprocess steps.
  - For each image, convert it to a video clip of the required segment duration (`clip_dur = (total_dur + (n_clips - 1) * FADE_DUR) / n_clips` if `n_clips > 1` else `total_dur`) using FFmpeg (crop/scale to 1080x1920 at 30 fps, pix_fmt `yuv420p`).
  - Implemented dynamic encoder selection via `get_h264_encoder()` (e.g. using `libopenh264` if `libx264` is missing) for BOTH `convert_image_to_video_clip` and `render_video_ltx` / `preprocess_clip` calls to prevent errors on environments missing `libx264`.
- Modified `scripts/run_slideshow.py` to:
  - Add `--image-urls` CLI argument.
  - Wrap `download_manual_images` in a `try...except` block, downloading to `img_dir`. If it fails, fall back to automatic DuckDuckGo image search.
  - Bypasses DuckDuckGo search and uses downloaded manual images directly if successful.

## 2. Logic Chain
- Standard `urllib.request` handles download and raises standard exceptions on HTTP or network errors, wrapping them in a clear `RuntimeError` as requested.
- In `run_short.py` and `run_slideshow.py`, the image paths are directly passed to `render_vertical_short()`, which dynamically scales and adjusts clip durations based on the count of images.
- In `run_short_ltx.py`, we convert static images to `.mp4` video clips using `-loop 1` option in FFmpeg. Bypassing the preprocess step and directly inserting the converted clips to `processed_video_paths` satisfies the rendering pipeline requirements.
- By dynamically retrieving the H.264 encoder via `get_h264_encoder()` and conditionally stripping `-preset` and `-crf` flags when `libx264` is unavailable, we prevent pipeline crash on systems where the default H.264 encoder is `libopenh264` (such as the target CLI system).

## 3. Caveats
- Direct internet connectivity is required to download manual image URLs.
- If the aspect ratio of the manually provided image is significantly different from 9:16, it is scaled and cropped to fill 1080x1920, meaning horizontal sides of landscape images will be cropped out.

## 4. Conclusion
The manual image downloading, validation, processing, and rendering flows are fully implemented across all three short automation scripts. All scripts were successfully verified through local dry-run executions, producing valid vertical `.mp4` outputs.

## 5. Verification Method
Verify the implementations by executing the following commands in the workspace root directory:

1. **Short Script Manual Mode Verification:**
   ```bash
   .venv/bin/python scripts/run_short.py --channel football --image-urls "https://picsum.photos/id/237/1080/1920,https://picsum.photos/id/1025/1080/1920"
   ```
   *Expected result:* Script finishes with exit status 0 and writes output to `output/runs/football_<timestamp>/short.mp4`.

2. **LTX Short Script Manual Mode Verification:**
   ```bash
   .venv/bin/python scripts/run_short_ltx.py --channel football --image-urls "https://picsum.photos/id/237/1080/1920,https://picsum.photos/id/1025/1080/1920"
   ```
   *Expected result:* Script converts static images into mp4 clips, stitches them using dynamic H264 encoder, and outputs final `short.mp4`.

3. **Slideshow Script Manual Mode Verification:**
   ```bash
   .venv/bin/python scripts/run_slideshow.py --channel football --image-urls "https://picsum.photos/id/237/1080/1920,https://picsum.photos/id/1025/1080/1920"
   ```
   *Expected result:* Script runs Ken Burns slideshow generation directly with the downloaded images and writes output `short.mp4`.
