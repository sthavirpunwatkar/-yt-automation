# E2E Test Infrastructure & Image Processing Analysis

## Executive Summary
This report analyzes the image and video downloading/processing workflows within the `yt-automation` codebase, specifically examining `scripts/run_short_ltx.py`, `scripts/run_slideshow.py`, and `scripts/fifa_orchestrator.py`. It identifies how assets are currently generated or fetched, specifies current command-line entry points, and provides a comprehensive design for an End-to-End (E2E) test runner and testing framework based on `pytest`. A 4-tier E2E testing strategy is recommended to ensure robust feature coverage, boundary handling, integration flow, and real-world compliance without incurring prohibitive cost or execution times.

---

## 1. Current Image & Video Workflows

Across the pipeline, assets (images and videos) are fetched dynamically from external sources. The detailed mechanisms are outlined below:

### A. Text-to-Video Workflow (`scripts/run_short_ltx.py`)
This script executes a text-to-video pipeline by communicating with the DeAPI txt2video endpoint.
1. **Prompt Generation:** Using Groq script generation (with the channel preset segment count set to 8), the script generates a list of 8 video scene text prompts from `pack["image_prompts"]`.
2. **DeAPI Job Submission:**
   - The script iterates through the 8 prompts, appending a preset style suffix.
   - It submits a JSON payload to `https://api.deapi.ai/api/v1/client/txt2video` containing the prompt, model (`Ltx2_3_22B_Dist_INT8`), dimensions ($576 \times 1024$ for vertical 9:16), frame count ($97$ frames, corresponding to ~4.04s at 24fps), and a random integer seed.
   - **Token Rotation & Limits:** It attempts to use the primary token from the `.env` variable (`DEAPI_TOKEN`) and falls back to a pool of 6 hardcoded backup tokens if rate limits (HTTP 429) or credit/payment limits (HTTP 400, 402, 422 containing credit-related keywords) are hit.
3. **Status Polling:**
   - It polls `https://api.deapi.ai/api/v1/client/request-status/<request_id>` up to 150 times (with a 5-second sleep in between) using the token that successfully submitted the request.
   - On completion (status `completed`, `success`, or `done`), it downloads the video file bytes via `result_url` using `httpx`.
4. **Processing & Stitching:**
   - The raw `.mp4` video clips are saved under `output/runs/<channel>_ltx_<timestamp>/videos/raw_clip_*.mp4`.
   - Each raw clip is preprocessed via FFmpeg (scaled and cropped to $1080 \times 1920$, and speed-adjusted via `setpts` filter to match the target segment duration derived from the total audio length: `(audio_duration + 7 * FADE_DUR) / 8`).
   - The final video is stitched in FFmpeg using randomly selected transition effects (e.g., `dissolve`, `slideleft`, `wipeleft`) and overlaid with SRT subtitles (rendered using fonts from `assets/fonts/` copied into a temp folder).

### B. Image Slideshow Workflow (`scripts/run_slideshow.py` & `pipeline/web_images.py`)
This script downloads static images from the web and stitches them into a vertical slideshow.
1. **Query Generation:** Groq generates narration along with a list of search queries from `pack.get("visual_search_queries", [])` (usually 25 queries).
2. **DuckDuckGo Image Search:**
   - It utilizes `DDGS()` (from the `ddgs` library) via the function `fetch_web_image()` to search for `"<query> hd -alamy -getty -shutterstock -stock -dreamstime -istock -123rf -depositphotos"` to exclude watermarked images.
   - It queries with `safesearch="off"`, `size="Large"`, and request size `max_results=30`.
3. **Image Download & Validation:**
   - For each query, it iterates through search results trying to download the image URL using `httpx.Client.get` (15s timeout).
   - **Magic Byte Check:** To filter out broken links or HTML error pages disguised as images, it verifies that the response bytes start with JPEG (`\xff\xd8\xff`), PNG (`\x89PNG\r\n\x1a\n`), or WebP/RIFF (`RIFF`) headers.
   - If verified, the bytes are saved locally as `img_*.jpg`.
   - **Fallback Mechanism:** If all 30 search results fail to download, the script copies the last successfully downloaded image as a duplicate fallback (`img_*_fallback.jpg`).
4. **Rendering:** The list of image paths is processed by `render_vertical_short()` (imported from `pipeline/render_short.py`), which generates Ken Burns pan/zoom effects (varying between zoom-in and zoom-out angles) and stiches the images together with crossfades and subtitles.

### C. Standard Image Workflow (`pipeline/images.py` & `pipeline/watermark_removal.py`)
Used by `scripts/run_short.py` and `scripts/test_sketch_images.py` for standard static image pipelines.
1. **DuckDuckGo Search:** Matches the search string but appends negative search tags like `-site:gettyimages.com -site:alamy.com -site:shutterstock.com -site:istockphoto.com`.
2. **Download:** Uses `httpx` with a browser-like `User-Agent` (to prevent HTTP 403 blocks) and verifies `Content-Type` headers (rejecting `text/html`).
3. **Automated Watermark Removal:**
   - Once saved to disk, the script feeds the image into `remove_watermark()`.
   - It uses `easyocr` to detect text boxes, builds a binary mask of text regions, dilates the mask using a $7 \times 7$ kernel to cover compression artifacts, and applies OpenCV's inpainting (`cv2.inpaint` with the `INPAINT_TELEA` algorithm) to heal the masked areas.

### D. Highlight Overlay Workflow (`scripts/fifa_orchestrator.py`)
This script generates shorts using video clips extracted from matches.
1. **YouTube Video Search:** Uses `yt-dlp` to search for "fifa 2026 highlights" (20 results) and grabs a video between 3 minutes and 60 minutes long.
2. **Clip Extraction:** It invokes an external tool `AI-Youtube-Shorts-Generator` (configured via `YOUTUBE_SHORT_GEN_DIR`) using a subprocess command to crop 4 vertical 9:16 clips from the downloaded highlights video and output metadata to `result.json`.
3. **Audio/Sub Overlay:** It reads `result.json` and runs a voiceover + subtitle overlay on top of the raw clip backgrounds using `render_video_background_short()`.
4. **Robust Fallback:** If video scraping/generation fails (e.g., due to a YouTube IP block), the script catches the exception, prints a warning, and immediately invokes the Image Slideshow engine (`run_slideshow.py`) as a fallback with `--upload` enabled.

---

## 2. Command-Line Entry Points & Gaps

Currently, the command-line arguments are structured around generating content on the fly via LLM/APIs rather than inputting local files.

| Script | Primary CLI Arguments | Image/Video Entry Points & Inputs |
| :--- | :--- | :--- |
| `scripts/run_short_ltx.py` | `--channel`, `--topic`, `--upload`, `--instagram`, `--facebook`, `--privacy` | **No direct entry point.** Video prompts are generated dynamically by Groq. Video files are fetched from DeAPI. |
| `scripts/run_slideshow.py` | `--channel`, `--topic`, `--upload`, `--instagram`, `--facebook`, `--privacy` | **No direct entry point.** Image queries are generated dynamically by Groq. Image files are scraped from DuckDuckGo. |
| `scripts/fifa_orchestrator.py` | None (reads `sys.argv` for `--upload` to feed into fallback script) | **No direct entry point.** Searches YouTube for video highlights using `yt-dlp` and processes them via external scripts. |
| `scripts/run_short.py` | `--channel` (req), `--topic`, `--upload`, `--instagram`, `--facebook`, `--privacy` | **No direct entry point.** Image prompts are generated dynamically by Groq. Image files are fetched from DDG. |
| `scripts/test_sketch_images.py`| Positional `topic_key` (`teenager`, `harrypotter`, `schoolstory`) | Selects hardcoded presets of image scene prompts. Reads image size and output parameters from environment variables (`HF_IMAGE_WIDTH`, `HF_IMAGE_HEIGHT`). |

### Identified Gaps:
* **No Local Media Inputs:** There is no command-line argument (e.g., `--images-dir` or `--video-clips`) to pass pre-downloaded images or video files to bypass the scraping/generation stage.
* **No Manual Prompt/Query Overrides:** You cannot supply a list of custom image search queries or custom text-to-video prompts via the CLI; prompts must always originate from Groq or hardcoded arrays inside the script files.
* **No Dry-Run Mode:** You cannot run the scripting/downloading stages without initiating the heavy FFmpeg rendering process.

---

## 3. E2E Test Runner & Framework Design

To test the video creation pipelines without hitting rate limits, executing slow API calls, or performing heavy rendering on every test run, we propose a modular `pytest`-based test suite.

### Proposed Directory Layout
```
/home/sp/Public/my_project/yt-automation/
├── tests/
│   ├── conftest.py             # Global pytest fixtures and CLI options
│   ├── assets/
│   │   ├── dummy_audio.mp3     # 1-second silent audio template
│   │   ├── dummy_image.jpg     # 1x1 pixel image file
│   │   └── dummy_video.mp4     # 1-second vertical H.264 video
│   ├── e2e/
│   │   ├── run_e2e_tests.py    # Main E2E runner CLI script
│   │   ├── test_ltx.py         # E2E test cases for run_short_ltx.py
│   │   ├── test_slideshow.py   # E2E test cases for run_slideshow.py
│   │   └── test_fifa.py        # E2E test cases for fifa_orchestrator.py
```

### Mocking & Acceleration Strategy
1. **API Mocking via `responses` / `pytest-mock`:**
   - **Groq API:** Mock the Groq client response to return static JSON payloads containing predictable script structures, title, narration, and image prompts.
   - **DeAPI txt2video:** Mock the `/client/txt2video` and `/client/request-status/<id>` endpoints. The mock returns a dummy request ID, and the status API transitions from `pending` to `completed` with a URL pointing to a mock video asset.
   - **DuckDuckGo Image Search:** Stub `ddgs.images` to return a list of local file URIs or mock HTTP endpoints hosting the dummy image asset.
   - **YouTube / Meta Upload APIs:** Mock upload endpoints to return dummy video IDs without uploading.
2. **FFmpeg Rendering Acceleration:**
   - The test suite overrides image/video processing paths. Instead of generating high-resolution videos, the E2E framework replaces downloaded assets with the 1-second dummy assets in `tests/assets/`.
   - This shortens video rendering from minutes to less than 2 seconds, while still exercising the complete FFmpeg filter chains and subtitle overrides.

### Test Runner Design (`tests/e2e/run_e2e_tests.py`)
The runner script will wrap `pytest` and provide clear controls over the execution environment.

```python
# Pseudo-code sketch for tests/e2e/run_e2e_tests.py
import argparse
import sys
import pytest
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="yt-automation E2E Test Runner")
    parser.add_argument("--tier", choices=["1", "2", "3", "4", "all"], default="all",
                        help="E2E Tier to run: 1=Feature, 2=Boundary, 3=Cross-Feature, 4=Real-world")
    parser.add_argument("--mode", choices=["mocked", "live", "record"], default="mocked",
                        help="Execution mode: mocked (default), live (real API hits), record (VCR mode)")
    parser.add_argument("--channel", help="Filter tests for a specific channel preset")
    parser.add_argument("--fast", action="store_true", default=True,
                        help="Substitute fast 1-second media assets for rendering speedup")
    args = parser.parse_args()

    # Build pytest arguments
    pytest_args = ["-v"]
    
    # Tier mapping to pytest marks
    if args.tier != "all":
        pytest_args.extend(["-m", f"tier{args.tier}"])
    
    # Custom flags processed in conftest.py
    pytest_args.extend([
        f"--test-mode={args.mode}",
        f"--fast-render={'true' if args.fast else 'false'}"
    ])
    if args.channel:
        pytest_args.extend(["-k", args.channel])

    print(f"Starting E2E Tests. Tier: {args.tier} | Mode: {args.mode} | Fast Render: {args.fast}")
    result = pytest.main(pytest_args)
    sys.exit(result)

if __name__ == "__main__":
    main()
```

---

## 4. Recommendations for the 4-Tier E2E Test Suite

### Tier 1: Feature Coverage (Functional Validation)
* **Goal:** Verify that each individual pipeline script completes a successful execution from end-to-end under normal parameters.
* **Mock Requirements:**
  - Mock Groq response for a specific channel ID (e.g., `fifa_2026`).
  - Stub `httpx` to return mock image bytes (for `run_slideshow.py`) and mock video bytes (for `run_short_ltx.py`).
  - Stub upload procedures.
* **Verification Assertions:**
  - Check that a run directory is created under `output/runs/`.
  - Validate that `script.json`, `voiceover.mp3`, `captions.srt`, and final video `short.mp4` exist.
  - Verify that FFmpeg exited with code 0 and successfully generated the output file.

### Tier 2: Boundary & Robustness (Error & Limit Handling)
* **Goal:** Verify that the system tolerates failures, rate-limiting, and bad data without crashing.
* **Test Scenarios:**
  - **DeAPI Token Rotation:** Mock the first DeAPI token to return HTTP 429, the second to return HTTP 400 (credit limit error), and the third to return HTTP 200. Verify the client correctly rotates through the token array and completes the job.
  - **Network Failures during Polling:** Simulate random connection failures during LTX status checks. Verify that the polling function retries and eventually succeeds.
  - **Malformed Media & Content Filters:** Mock DuckDuckGo Image Search to return HTML content-type or non-image bytes (e.g. error texts). Check that the magic byte check in `web_images.py` identifies the mismatch, skips the file, and proceeds to the next URL or invokes the duplicate-fallback routine.
  - **Empty Results:** Return zero search results from the DDG search query. Verify that the script terminates gracefully with exit code 1 or executes correct error handling.

### Tier 3: Cross-Feature & Integration (Multi-Step Coordination)
* **Goal:** Verify interaction between multiple components or configurations.
* **Test Scenarios:**
  - **Orchestrator Fallback Workflow:** Mock `yt-dlp` in `fifa_orchestrator.py` to raise a simulated network or IP block exception. Verify that the orchestrator catches this failure and calls `run_slideshow.py` with `--upload` as a fallback, executing the slideshow pipeline successfully.
  - **Bilingual Flow Validation:** Set the channel preset to a bilingual variant (e.g. Hindi/English variants sharing the same images). Verify that two separate final videos are rendered (`short_en.mp4` and `short_hi.mp4`), each matching its corresponding audio and caption file, while images are downloaded only once.
  - **Multi-Platform Publishing Integration:** Run a script with `--upload`, `--instagram`, and `--facebook` options activated. Assert that the final video is routed to:
    1. YouTube Upload API client.
    2. Instagram Reels Graph API client.
    3. Facebook Page Reels Graph API client.
    Verify that failure on one platform does not block publishing on the other platforms.

### Tier 4: Real-World & Golden Master (Live Verification)
* **Goal:** Validate that final output videos conform to platform publishing specs and check live API connections.
* **Verification Method:**
  - Execute a live run using valid API tokens (without uploading, or uploading to a test/private playlist).
  - **Structural Video Scan:** After compilation, use `ffprobe` to verify the generated `short.mp4` structure:
    - Resolution must be exactly $1080 \times 1920$ (vertical 9:16).
    - Video Codec is `h264` (or `openh264`).
    - Audio Codec is `aac`.
    - Video duration must match the audio soundtrack duration within a $\pm0.5$-second tolerance.
    - Check that the file size is non-zero and playable.

---

## 5. Implementation Roadmap

1. **Phase 1: Mock Setup & Core Fixtures:** Build `tests/conftest.py` with the environment overrides, `vcrpy` / `responses` setup, and local test assets (dummy image, video, audio).
2. **Phase 2: Tier 1 & Tier 2 for Slideshows:** Implement tests for `run_slideshow.py` and `pipeline/web_images.py` due to their lower complexity. Write tests for image magic byte detection and fallback.
3. **Phase 3: Tier 1 & Tier 2 for LTX & Orchestrator:** Add tests for `run_short_ltx.py` (specifically token rotating logic and polling timeout) and `fifa_orchestrator.py` (simulating external CLI command executions and `yt-dlp` returns).
4. **Phase 4: Fallback & Cross-Feature Integration (Tier 3):** Implement the multi-variant flow tests and orchestrator-to-slideshow fallback integration test.
5. **Phase 5: Golden Master & FFprobe Checks (Tier 4):** Write the post-render validation tests to dynamically audit video properties. Introduce the main test runner `run_e2e_tests.py` to command all tests.
