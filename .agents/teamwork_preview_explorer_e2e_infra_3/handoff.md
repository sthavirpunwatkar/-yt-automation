# Handoff Report — E2E Test Infrastructure Design

## 1. Observation

Direct observations made within the `yt-automation` codebase:
* **Slideshow Image Fetching & Magic Bytes**: In `pipeline/web_images.py` lines 41-47:
  ```python
  with httpx.Client(timeout=15.0) as client:
      resp = client.get(image_url)
      resp.raise_for_status()
      
      # Verify it's actually an image by checking magic bytes
      content = resp.content
      if not (content.startswith(b'\xff\xd8\xff') or content.startswith(b'\x89PNG\r\n\x1a\n') or content.startswith(b'RIFF')):
  ```
  If magic bytes check fails, it skips the image.
* **Token Rotation**: In `scripts/run_short_ltx.py` lines 45-53, a token pool is configured:
  ```python
  DEAPI_TOKENS = [
      os.environ.get("DEAPI_TOKEN", "").strip(),
      "vvQBZjPmi2NFQIfFpgl0Tg0F0bL3Q089zEuCBDwpdf592e0e",
      ...
  ]
  ```
  In lines 123-134, rate limiting and credit limit errors cause token index incrementing:
  ```python
  if resp.status_code == 429 or is_credit_limit:
      print(f"      Token {preview} hit limits. Rotating to next token...")
      current_token_idx += 1
  ```
* **Orchestrator Fallback**: In `scripts/fifa_orchestrator.py` lines 170-181:
  ```python
  except Exception as e:
      print(f"Video scraping failed (likely YouTube IP block): {e}")
      print("Gracefully falling back to the robust Image Slideshow engine...")
      ...
      try:
          # Force the upload flag so the fallback actually publishes to YouTube!
          sys.argv = [sys.argv[0], "--upload"]
          import run_slideshow
          run_slideshow.main()
  ```
* **CLI Gaps**: Using `grep_search` to find `ArgumentParser` in `run_short.py`, `run_short_ltx.py`, and `run_slideshow.py` showed that none of them contain options such as `--image-dir`, `--video-dir`, or `--image-queries`. Arguments are restricted to config parameters like `--channel`, `--topic`, `--upload`, `--instagram`, `--facebook`, and `--privacy`.
* **Peer Reports**: Read analysis files in `.agents/teamwork_preview_explorer_e2e_infra_1/analysis.md` and `.agents/teamwork_preview_explorer_e2e_infra_2/analysis.md`, which confirm consensus on using `pytest` and mock dummy assets in `tests/assets/` to accelerate FFmpeg runs.

---

## 2. Logic Chain

1. **Deterministic Rendering Verification**: To test the video rendering pipeline without hitting external APIs or generating large media files, we must pass local deterministic images and audios.
2. **Current Entry Point Gap**: Because current CLI tools (`run_slideshow.py`, `run_short_ltx.py`) do not accept local directory inputs or manually supplied search queries (Observation 4), they cannot be natively targeted with local assets without modifications.
3. **Mocking Strategy**: By globally mocking out the external boundaries (`groq`, `httpx`, `DDGS`, `synthesize_full`, and the platform upload libraries) using pytest fixtures (Observation 5), we can redirect network downloads to local files.
4. **Acceleration Execution**: By copying a 1-second dummy silent MP3 and 1-pixel JPG into the media pipeline during mocked runs, FFmpeg runs in <2 seconds rather than minutes, which satisfies CI pipeline speed constraints.
5. **Orchestrator Fallback Routing**: The exception handler in the orchestrator fallback (Observation 3) must be explicitly tested. Mocking `yt-dlp` to fail should trigger the fallback to `run_slideshow.main()`, which verifies Tier 3 cross-feature logic.

---

## 3. Caveats

* **FFmpeg Availability**: The E2E tests assume that FFmpeg and ffprobe are installed and available in the environment's `PATH`. If missing, the tests will raise a `RuntimeError` (simulated in Tier 2, but a blocker for live execution).
* **Mock Fidelity**: The mock Groq API and DeAPI responses must closely follow the JSON structures currently used in the production pipeline (e.g. `visual_search_queries` vs `image_prompts`). If the production API changes its schema, the mocked E2E tests might pass while live executions fail.
* **IP Blocks in CI**: Tier 4 tests execute live network calls, which are prone to failures in CI if YouTube blocks the runner's IP address when running `yt-dlp`.

---

## 4. Conclusion

A 4-tier E2E testing framework using `pytest` is highly feasible and recommended:
1. **Tier 1 (Feature Coverage)**: Validates single pipeline flow, bilingual variations, and watermark inpainting using a local mock sandbox.
2. **Tier 2 (Boundary & Robustness)**: Verifies token rotation, empty search results, corrupt download bytes, and missing dependencies.
3. **Tier 3 (Cross-Feature)**: Validates the highlight scraper fallback to the slideshow engine and multi-platform publishing.
4. **Tier 4 (Real-world)**: Evaluates live token dry-runs and checks generated MP4 files with `ffprobe` for correct dimensions, formats, and audio-video sync.

To make the system testable, the codebase should be extended to accept `--image-dir` as a CLI override in generator scripts.

---

## 5. Verification Method

To verify the E2E test framework design:
1. Ensure the pytest suite layout (`tests/conftest.py`, `tests/e2e/`, `tests/assets/`) is created.
2. Run the test command:
   ```bash
   pytest tests/
   ```
   Or run the runner wrapper directly:
   ```bash
   python tests/e2e/run_e2e_tests.py
   ```
3. Inspect the `analysis.md` report at `.agents/teamwork_preview_explorer_e2e_infra_3/analysis.md` to confirm the design meets all objectives.
