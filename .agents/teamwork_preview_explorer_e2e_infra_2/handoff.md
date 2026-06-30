# Handoff Report - E2E Test Infrastructure & Image Pipeline

## 1. Observation
- `scripts/run_slideshow.py` (lines 111-112) calls `fetch_web_image`:
  ```python
  status, detail = fetch_web_image(strict_query, out_path)
  ```
- `pipeline/web_images.py` (lines 19-20) queries DuckDuckGo Search:
  ```python
  with DDGS() as ddgs:
      results = ddgs.images(
  ```
- `scripts/run_short_ltx.py` (lines 404-407) submits prompts to DeAPI and polls status:
  ```python
  request_id, successful_token = submit_video(full_prompt, client)
  ...
  video_bytes = poll_video(request_id, successful_token, client)
  ```
- `scripts/fifa_orchestrator.py` (lines 41-45) searches highlights using `yt-dlp`:
  ```python
  cmd = [sys.executable, "-m", "yt_dlp", "ytsearch20:fifa 2026 highlights", "-J"]
  ```
- `pipeline/render_short.py` (lines 91-102) implements video rendering:
  ```python
  def render_vertical_short(
      image_paths: list[Path],
      total_duration: float,
      audio_path: Path,
      srt_path: Path,
      out_video: Path,
  ```
- There is currently no `tests/` directory or testing infrastructure in the project root.
- The command-line inputs (`--channel`, `--topic`, `--upload`, `--instagram`, `--facebook`, `--privacy`) do not allow specifying local images or manual search queries directly.

## 2. Logic Chain
- **Step 1**: The observations show that all images and video clips are dynamically retrieved at runtime via external network requests (DuckDuckGo, DeAPI, YouTube highlights via `yt-dlp`).
- **Step 2**: The observations also show that FFmpeg is used to process and stitch the images/video clips together (cropping to 1080x1920, applying Ken Burns zoompan filters, crossfades, caption overlays).
- **Step 3**: Because these pipelines are heavily network-dependent, rate-limited, and slow, testing them in a CODE_ONLY environment requires full offline isolation.
- **Step 4**: Therefore, the test runner must mock all API wrappers (Groq, DDGS, DeAPI, Edge TTS, Uploads) and run FFmpeg on lightweight, short dummy assets (silence audio, 1-second images/videos) to keep tests fast and completely local.
- **Step 5**: The lack of a `tests/` folder means the framework structure and runner script (`tests/e2e/run_e2e_tests.py`) must be designed from scratch. We recommend `pytest` due to conftest fixture sharing and simple parameterization.
- **Step 6**: By categorizing tests into a 4-tier suite (Feature Coverage, Boundary, Cross-Feature, Real-world), the framework can verify happy-paths, rate-limiting rotation resilience, failure fallbacks, and complete end-to-end command-line executions.

## 3. Caveats
- No code was written to the project codebase itself, in line with the read-only Explorer constraints.
- The external library `AI-Youtube-Shorts-Generator` was not examined beyond its subprocess invocation wrapper in `fifa_orchestrator.py` because its source code is outside the `yt-automation` workspace.

## 4. Conclusion
- A `pytest`-based offline test runner is the optimal choice to verify the `yt-automation` pipeline. A complete design blueprint, conftest mocking strategy, and a 4-tier E2E test plan have been structured and documented in `analysis.md`.

## 5. Verification Method
- **Inspection**: View `/home/sp/Public/my_project/yt-automation/.agents/teamwork_preview_explorer_e2e_infra_2/analysis.md` to confirm all findings, CLI inputs, pytest architectures, conftest mock templates, and 4-tier test recommendations are fully documented.
- **Invalidation Condition**: This analysis will be invalidated if the project introduces a non-Python-based execution layer, or if additional third-party network APIs are introduced without corresponding mock coverage in `conftest.py`.
