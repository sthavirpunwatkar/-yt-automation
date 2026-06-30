# Unified E2E Test Infrastructure & Image Processing Analysis

## Executive Summary
This report presents a synthesized, read-only analysis of the asset downloading, preprocessing, rendering, and publishing pipelines in the `yt-automation` codebase. By examining the current implementation of `scripts/run_short_ltx.py`, `scripts/run_slideshow.py`, and `scripts/fifa_orchestrator.py`, we identify image and video processing flows, list CLI entry points, and propose a comprehensive design for a `pytest`-based End-to-End (E2E) testing framework.

To avoid costly API calls, rate-limiting, and slow CPU-heavy video rendering in testing environments, we outline a structured mocking strategy utilizing dummy assets and a **4-tier E2E testing hierarchy** (Feature Coverage, Boundary, Cross-Feature, and Real-world).

---

## 1. Catalog of Sources and Synthesis Approach
In compliance with the teamwork synthesis protocol, this analysis integrates observations, verification results, and plans compiled across the following sources:
1. **Source A (`teamwork_preview_explorer_e2e_infra_1/analysis.md`)**: Analyzed token rotation pools, magic byte checks, and proposed a custom argument-driven E2E test runner (`run_e2e_tests.py`).
2. **Source B (`teamwork_preview_explorer_e2e_infra_2/analysis.md`)**: Analyzed OpenCV/EasyOCR watermark removal pipelines and drafted detailed mocking implementations for Groq, DDG, DeAPI, and Edge TTS.
3. **Primary Verification**: Direct codebase review using read-only filesystem tools of `scripts/` and `pipeline/` modules.

All findings are reconciled under a unified evidence chain. No dissenting views were identified; the peer analyses are highly complementary, with Source A detailing video-concatenation/stitching, and Source B highlighting watermark-removal and mock python code snippets.

---

## 2. Image & Video Processing Workflows

Across the repository, asset downloading and processing are handled dynamically:

### A. Text-to-Video Generation (`scripts/run_short_ltx.py`)
* **Prompt Definition**: Groq generated scripts return detailed visual descriptions under `pack["image_prompts"]` (configured to $8$ segments).
* **DeAPI Request & Token Rotation**:
  * Prompts are modified with a preset-defined style suffix.
  * Payloads are submitted to `https://api.deapi.ai/api/v1/client/txt2video` ($576 \times 1024$ resolution, $97$ frames, 24fps).
  * The script maintains a pool of $7$ DeAPI tokens (`DEAPI_TOKENS`). If a token encounters rate limits (HTTP 429) or credit exhaustion errors (HTTP 400, 402, 422 with keywords like "credit", "limit"), it automatically rotates to the next token and retries (up to $2 \times$ the token pool size).
* **Polling & Download**: Checks `https://api.deapi.ai/api/v1/client/request-status/<id>` every 5 seconds (up to 150 times) using the token that successfully submitted the request. The final MP4 bytes are fetched via `result_url`.
* **Preprocessing & Stitching**:
  * Preprocessing uses FFmpeg to scale and crop clips to $1080 \times 1920$ and speed-adjust them (`setpts=PTS*(target_dur/orig_dur)`) to fit the audio clip window at 30fps.
  * Concatenates clips with a random xfade transition style (e.g. `dissolve`, `fade`, `slideleft`) and overlays SRT subtitles using local fonts.

### B. Web Image Slideshows (`scripts/run_slideshow.py` & `pipeline/web_images.py`)
* **Search Query Generation**: Groq generates a list of search queries (`pack["visual_search_queries"]`).
* **Scraping**: DuckDuckGo Image Search (`ddgs.images`) is invoked for each query with `" FIFA World Cup football match"` appended for strict sports matching. It excludes domain watermarks using negative filters (e.g., `-alamy -getty -shutterstock`).
* **Magic Byte Validation**: Downloaded HTTP responses are validated against file signatures before saving:
  * JPEG: starts with `\xff\xd8\xff`
  * PNG: starts with `\x89PNG\r\n\x1a\n`
  * WebP: starts with `RIFF`
* **Fallback**: If all 30 search results fail to download, it duplicates the last successful image to prevent pipeline crashes.
* **Ken Burns & Slideshow Stitching**: Pre-scales images to $1080 \times 1920$ and applies dynamic zoom and pan patterns (zoom-in/zoom-out drifting towards anchors). Clips are crossfaded via FFmpeg `xfade` (0.45s fade duration) and mixed with TTS audio and subtitles.

### C. Standard Image Pipelines (`pipeline/images.py` & `pipeline/watermark_removal.py`)
* Used by `scripts/run_short.py` and `scripts/test_sketch_images.py`.
* **Watermark Inpainting**: Downloaded images are parsed by OpenCV (`cv2`) and `easyocr`.
* **OCR Masking**: Any detected English text with confidence $\ge 0.2$ is added to a binary mask. The mask is dilated using a $7 \times 7$ kernel to cover compression artifacts, and inpainted via OpenCV's Telea algorithm (`cv2.inpaint(..., cv2.INPAINT_TELEA)`).

### D. Highlight Processing (`scripts/fifa_orchestrator.py`)
* **Video Scraping**: Searches YouTube using `yt-dlp` for `"fifa 2026 highlights"` and selects a video between 3 and 60 minutes long.
* **Clip Generation**: Invokes `AI-Youtube-Shorts-Generator` (`main.py`) as a subprocess to extract $4$ vertical 9:16 clips.
* **Audio Overlay**: Overlays synthesized voiceover and captions onto the extracted highlights.
* **Orchestrator Fallback**: If the video scraping fails (e.g. due to YouTube IP blocks), the orchestrator catches the exception and falls back to running `run_slideshow.main()`.

---

## 3. Command-Line Entry Points & Gaps

The primary CLI entry points do not accept custom image files or local directories, relying entirely on dynamically generated assets.

| Script File | CLI Arguments | Image / Asset Control Entry Point |
| :--- | :--- | :--- |
| `scripts/run_short_ltx.py` | `--channel`, `--topic`, `--upload`, `--instagram`, `--facebook`, `--privacy` | None. Video prompts generated via Groq; video clips fetched via DeAPI. |
| `scripts/run_slideshow.py` | `--channel`, `--topic`, `--upload`, `--instagram`, `--facebook`, `--privacy` | None. Search queries generated via Groq; images fetched via DuckDuckGo. |
| `scripts/fifa_orchestrator.py` | None | None. Scrapes highlights from YouTube and cuts clips using an external CLI. |
| `scripts/run_short.py` | `--channel`, `--topic`, `--upload`, `--instagram`, `--facebook`, `--privacy` | None. Image prompts generated via Groq; images fetched via DDG. |
| `scripts/test_sketch_images.py`| Positional `topic_key` (`teenager`, `harrypotter`, `schoolstory`) | Bypasses Groq. Downloads images using hardcoded topic visual prompts. |

### Gaps for E2E Testability:
1. **Lack of Local Asset Injection**: No command-line arguments (like `--image-dir` or `--video-dir`) exist to point scripts to local directories of test images/videos. This prevents offline E2E verification of the rendering engine.
2. **Lack of Query Overrides**: There is no way to pass custom image search queries directly from the CLI to bypass Groq generation.
3. **No Render-only Dry Run**: No CLI flag is available to test the script/asset downloading pipelines without triggering the slow FFmpeg video encoding.

---

## 4. E2E Test Framework & Runner Design

We propose setting up a structured `pytest` testing framework in the project root under `tests/`.

### Directory Layout
```
/home/sp/Public/my_project/yt-automation/
├── tests/
│   ├── conftest.py             # Global pytest overrides, fixtures, and mocks
│   ├── assets/                 # Lightweight dummy assets (very small size)
│   │   ├── dummy_image.jpg     # 1x1 solid black image
│   │   ├── dummy_audio.mp3     # 1-second silent MP3
│   │   └── dummy_video.mp4     # 1-second 1080x1920 vertical H.264 video
│   └── e2e/
│       ├── run_e2e_tests.py    # CLI E2E test runner wrapper script
│       ├── test_run_short.py   # E2E tests for run_short.py
│       ├── test_ltx.py         # E2E tests for run_short_ltx.py
│       ├── test_slideshow.py   # E2E tests for run_slideshow.py
│       └── test_fifa.py        # E2E tests for fifa_orchestrator.py
```

### Proposed Mocks for Code-Only CI Execution

The E2E tests will run entirely offline using pytest mocks defined in `tests/conftest.py`:

1. **Groq Client Mock**:
   Mocks `groq.Groq.chat.completions.create` to return a predefined JSON response containing dummy titles, descriptions, narrations, prompts, and search queries.

2. **DuckDuckGo Fetch Mock**:
   Stubs `pipeline.web_images.fetch_web_image` or the `DDGS` search client. In mock mode, this immediately copies `tests/assets/dummy_image.jpg` to the target path and returns `"ok"`.

3. **DeAPI Client Mock**:
   Stubs `submit_video` and `poll_video` in `run_short_ltx.py` to immediately write the content of `tests/assets/dummy_video.mp4` to the output video directory, bypassing DeAPI endpoints.

4. **Edge TTS Mock**:
   Stubs `pipeline.edge_tts_synth.synthesize_full` to copy `tests/assets/dummy_audio.mp3` to the target destination and return a fixed duration and sentence alignment dictionary.

5. **Upload API Mock**:
   Stubs `pipeline.youtube_upload.upload_short`, `publish_instagram_reel`, and `publish_facebook_reel` to assert arguments and return dummy platform video IDs (`"mock_yt_123"`).

6. **FFmpeg Acceleration**:
   By replacing downloaded files with the 1-second dummy assets, FFmpeg compiles videos in less than 2 seconds, exercising the complex filters without exhausting CPU limits.

### Test Runner CLI (`tests/e2e/run_e2e_tests.py`)
```python
import argparse
import sys
import pytest

def main():
    parser = argparse.ArgumentParser(description="yt-automation E2E Test Suite Runner")
    parser.add_argument("--tier", choices=["1", "2", "3", "4", "all"], default="all",
                        help="Select E2E Tier: 1=Feature, 2=Boundary, 3=Cross-Feature, 4=Real-world")
    parser.add_argument("--mode", choices=["mocked", "live"], default="mocked",
                        help="Execution mode (mocked sandbox or live integration)")
    parser.add_argument("--channel", help="Filter by specific channel preset")
    args = parser.parse_args()

    pytest_args = ["-v", "-s", "tests/e2e"]
    if args.tier != "all":
        pytest_args.extend(["-m", f"tier{args.tier}"])
    
    pytest_args.extend([f"--mode={args.mode}"])
    if args.channel:
        pytest_args.extend(["-k", args.channel])

    print(f"Starting E2E tests in {args.mode} mode for Tier {args.tier}...")
    sys.exit(pytest.main(pytest_args))

if __name__ == "__main__":
    main()
```

---

## 5. 4-Tier E2E Test Suite Recommendations

We recommend dividing the test suite into 4 distinct tiers:

### Tier 1: Feature Coverage (Functional Completeness)
* **Goal**: Validate that all default pipelines run successfully end-to-end under normal operating conditions.
* **Key Tests**:
  * `test_slideshow_pipeline_flow`: Executes the slideshow pipeline. Asserts that `short.mp4`, `voiceover.mp3`, and `captions.srt` are generated inside the unique run folder and FFmpeg compiles successfully.
  * `test_ltx_video_pipeline_flow`: Executes the text-to-video pipeline. Confirms raw videos are preprocessed, speed-adjusted, and crossfaded with transition styles.
  * `test_bilingual_variant_flow`: Runs `run_short.py` using a bilingual preset. Asserts images are fetched once and shared, and two separate variant video files (e.g. `short_en.mp4`, `short_hi.mp4`) are generated.
  * `test_watermark_removal_logic`: Asserts OpenCV Telea inpainting successfully replaces text in a test image.

### Tier 2: Boundary (Error & Robustness Handling)
* **Goal**: Verify that the pipelines fail gracefully or recover from API and media format errors.
* **Key Tests**:
  * `test_deapi_token_rotation`: Mocks the first 3 DeAPI tokens to return HTTP 429 or HTTP 402, and the 4th token to return success. Asserts that the script correctly rotates tokens and succeeds.
  * `test_deapi_tokens_exhausted`: Mocks all tokens to fail. Asserts the script raises a `RuntimeError` stating that all tokens are exhausted.
  * `test_invalid_image_bytes`: Simulates a web download returning a text/HTML error page. Asserts that the magic byte check in `fetch_web_image` successfully detects the invalid file, rejects it, and moves to the next result.
  * `test_empty_search_results`: Mocks DuckDuckGo to return 0 search results. Asserts the slideshow script handles this gracefully (applies duplicate fallback or terminates with a clear exit code).
  * `test_missing_ffmpeg`: Mocks `shutil.which` to return `None` for FFmpeg. Asserts that a helpful `RuntimeError` is raised.

### Tier 3: Cross-Feature (Interoperability & Fallback Integration)
* **Goal**: Verify interactions between distinct scripts and cross-cutting workflow dependencies.
* **Key Tests**:
  * `test_fifa_orchestrator_scraper_fallback`: Mocks YouTube scraper/yt-dlp in `fifa_orchestrator.py` to raise a `RuntimeError`. Asserts that the orchestrator catches the exception, overrides arguments, invokes the Image Slideshow engine (`run_slideshow.main`), and successfully renders the video fallback.
  * `test_concurrency_isolation`: Runs two slideshow pipelines concurrently. Asserts that unique timestamped directories prevent collisions in temporary rendering outputs.
  * `test_multi_platform_upload_routing`: Mocks YouTube, Instagram, and Facebook upload calls. Asserts that a failure on one platform does not block publishing or video routing to other platforms.

### Tier 4: Real-World (Live Validation & Golden Master)
* **Goal**: Validate live API tokens, actual rendering output compliance, and history file logging.
* **Key Tests**:
  * `test_live_dryrun_slideshow`: Runs a live end-to-end slideshow generation using a test topic, checking that external APIs respond correctly (does not publish to live channels).
  * `test_rendered_video_spec_compliance`: Uses `ffprobe` to verify compiled MP4 files:
    * Resolution must be exactly $1080 \times 1920$ (vertical 9:16).
    * Video codec is `h264`, audio codec is `aac`.
    * Total video length matches audio track length (tolerance $\pm0.5$s).
  * `test_history_logging`: Asserts details are appended to `output/history/<channel>.json` and obeys history rotation size limits.
  * `test_manual_upload_routing`: Asserts that when `--upload` is disabled, the final video is correctly routed to the `upload yt/` directory with a sanitized title filename.

---

## 6. Synthesis Summary of Recommendations
* **Consensus**: Both Source A and Source B agree that `pytest` is the most appropriate framework. Using lightweight mock media assets in `tests/assets/` is critical to keep execution times fast.
* **Resolved Conflicts**: There were no conflicts between sources. Source B's detailed OCR-inpainting tests have been integrated into Tier 1, and Source A's FFmpeg filter chain validations have been integrated into Tier 4.
* **Gaps Addressed**: Identified the absolute lack of local asset injection in the production generation scripts. We recommend the implementer adds a `--image-dir` parameter to `run_slideshow.py` and `run_short_ltx.py` to decouple rendering tests from external APIs and allow testing with static directories of test images.
