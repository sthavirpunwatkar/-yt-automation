# E2E Test Infrastructure Explorer - Handoff Report

## 1. Observation
The following file paths, line ranges, and verbatim details were observed:
* **Text-to-Video Workflow (`scripts/run_short_ltx.py`):**
  * Lines 94-159: Submits text-to-video jobs. If HTTP 429 or credit limit errors are encountered, it rotates tokens via `current_token_idx += 1`.
  * Lines 160-201: Polls status using the token that successfully submitted the request. On completion, it fetches the resulting video bytes via `result_url`.
  * Lines 394-417: Runs a loop over `video_prompts` and saves raw clips:
    ```python
    video_bytes = poll_video(request_id, successful_token, client)
    clip_path = vid_dir / f"raw_clip_{i:02d}.mp4"
    clip_path.write_bytes(video_bytes)
    ```
* **Image Slideshow Workflow (`scripts/run_slideshow.py` and `pipeline/web_images.py`):**
  * `scripts/run_slideshow.py` (Lines 103-128) loops through `search_queries` and calls `fetch_web_image()` to fetch static images. If download fails, it copies the last successful image as a fallback.
  * `pipeline/web_images.py` (Lines 15-57) performs DDG search, downloads images via `httpx`, and performs a magic byte check:
    ```python
    content = resp.content
    if not (content.startswith(b'\xff\xd8\xff') or content.startswith(b'\x89PNG\r\n\x1a\n') or content.startswith(b'RIFF')):
        print(f"      [WebImages] Invalid image data (likely HTML) from {image_url}")
        continue
    ```
* **Image Fetching and Watermark Removal (`pipeline/images.py` and `pipeline/watermark_removal.py`):**
  * `pipeline/images.py` (Lines 64-94) saves scene images and uses EasyOCR-based watermark removal:
    ```python
    from pipeline.watermark_removal import remove_watermark
    remove_watermark(str(out_path), str(out_path))
    ```
  * `pipeline/watermark_removal.py` (Lines 14-47) loads the OCR reader, creates a binary mask of text regions, dilates it, and runs:
    ```python
    inpainted_img = cv2.inpaint(img, mask, 5, cv2.INPAINT_TELEA)
    ```
* **Video Highlight & Fallback Orchestration (`scripts/fifa_orchestrator.py`):**
  * Lines 39-59 search for highlights using `yt-dlp`.
  * Lines 61-75 run an external tool configured via `YOUTUBE_SHORT_GEN_DIR` (`AI-Youtube-Shorts-Generator` project).
  * Lines 164-186 catch errors and fall back to the Image Slideshow generator:
    ```python
    except Exception as e:
        print(f"Video scraping failed (likely YouTube IP block): {e}")
        print("Gracefully falling back to the robust Image Slideshow engine...")
        ...
        import run_slideshow
        run_slideshow.main()
    ```
* **Testing Infrastructure:**
  * There are currently no standard unit/integration/E2E test suites or folders (e.g. using `pytest` or `unittest`). All testing is done using ad-hoc runner scripts (like `scripts/test_sketch_images.py`).

## 2. Logic Chain
1. **Deduction on Asset Types:** `run_short_ltx.py` is fundamentally a text-to-video workflow fetching MP4 bytes from DeAPI, whereas `run_slideshow.py` is a static image scraping workflow fetching JPEG/PNG/WebP bytes from DuckDuckGo. E2E tests must isolate these distinct network-fetching protocols.
2. **Deduction on Fallbacks:** `fifa_orchestrator.py` is tightly coupled to the environment and YouTube's scrape limits. The fallback handler executes `run_slideshow.py` in case of failure. Testing this orchestration requires mocking `yt-dlp` shell outputs and simulating exceptions to verify fallback coverage.
3. **Deduction on Testing Requirements:** Running live E2E tests for video creation is expensive, slow, and prone to rate limits or IP blocks. Therefore, the E2E framework must mock external APIs (Groq, DeAPI, DuckDuckGo, YouTube, Meta) and mock or shorten the FFmpeg rendering phase (using 1-second dummy media clips) to keep tests fast, reliable, and offline-compatible.

## 3. Caveats
* The external generator repository in `/home/sp/Public/my_project/opensource-video/youtube_short_generator/AI-Youtube-Shorts-Generator` was not directly analyzed because it sits outside the active workspace. Its interfaces were inferred from `scripts/fifa_orchestrator.py`.
* Actual API keys and real-world uploads were not tested due to CODE_ONLY network restrictions.

## 4. Conclusion
* We recommend building the E2E test framework using `pytest` because of its rich support for fixtures, assertions, parameterization, and plugin ecosystem (e.g. `responses`, `pytest-mock`, `vcrpy`).
* We have proposed a 4-tier E2E structure (Feature Coverage, Boundary, Cross-Feature, Real-world) and detailed how to mock the APIs and FFmpeg processing to achieve robust coverage. The complete details are documented in `analysis.md` in the working directory.

## 5. Verification Method
* **Inspection:** Open and read `/home/sp/Public/my_project/yt-automation/.agents/teamwork_preview_explorer_e2e_infra_1/analysis.md` to verify it addresses all parts of the user request.
* **Codebase State:** Run `git status` in the repository root to confirm no codebase source code or tests files were modified or created, preserving the read-only exploration constraint.
