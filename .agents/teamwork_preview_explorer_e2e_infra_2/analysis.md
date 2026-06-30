# E2E Test Infrastructure & Image Pipeline Analysis

## 1. Executive Summary
This report analyzes the image/video acquisition and processing workflows in the `yt-automation` repository, examines the existing command-line entry points, and provides a comprehensive architectural design for an End-to-End (E2E) testing framework. 
Because the pipeline relies on several high-cost, rate-limited, and network-bound external APIs (Groq, DeAPI, Edge TTS, DuckDuckGo Search, YouTube/Instagram Uploads) and CPU-heavy FFmpeg tasks, a robust offline-first testing harness is required. We recommend a `pytest`-based E2E test runner that uses structured mocking, dummy assets, and a 4-tier testing hierarchy to achieve complete coverage, stability, and speed without triggering API charges, rate limits, or network violations.

---

## 2. Current Image/Video Downloading & Processing Logic

Across the codebase, three main scripts orchestrate different pipelines for asset downloading, preprocessing, and stitching.

### A. Web Image Slideshow Pipeline (`scripts/run_slideshow.py`)
1. **Script Pack Generation**: Calls `generate_short_pack` (defined in `pipeline/groq_script.py`), which uses the Groq API to return a JSON payload. This payload contains `visual_search_queries` generated from a text topic or rotation schema.
2. **Web Scraping / Image Downloading**:
   - For each search query, the script appends `" FIFA World Cup football match"` (for strict sports context) and delegates to `pipeline.web_images.fetch_web_image(query, out_path)`.
   - `fetch_web_image` queries DuckDuckGo Image Search (`ddgs.images`), applying negative keyword exclusions (`-alamy -getty -shutterstock -stock` etc.) to filter out heavy watermarks, and requests `Large` images.
   - It iterates through the search results and uses `httpx.Client.get` with a `15.0` second timeout.
   - **Validation via Magic Bytes**: The downloaded bytes are inspected to verify they start with magic headers for JPEG (`\xff\xd8\xff`), PNG (`\x89PNG\r\n\x1a\n`), or WebP (`RIFF`), ensuring HTML/error responses are ignored.
   - **Fallback Mechanism**: If an image search or download fails, the script copies the last successfully downloaded image as a duplicate fallback (`img_XX_fallback.jpg`) so the pipeline does not abort.
3. **Slideshow Rendering**:
   - Delegates to `render_vertical_short` in `pipeline/render_short.py`.
   - **Pre-scaling & Cropping**: Uses FFmpeg to scale and crop each image to 1080x1920 (9:16 aspect ratio) via the filter: `scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920`. This fills the canvas without black bars.
   - **Ken Burns Effect**: Each pre-scaled image is turned into a short MP4 clip using FFmpeg's `zoompan` video filter. A random pan expression is picked from a pre-configured pattern pool (`PAN_PATTERNS`) to alternate zooms and directional pans (e.g. top-left to center, zoom-out right-to-left).
   - **Stitching & Crossfades**: The generated clips are concatenated together using FFmpeg's `xfade` filter using a randomly selected transition style (e.g., `dissolve`, `fade`, `slideleft`) with a `0.45`s transition duration.
   - **Audio & Captions Overlay**: Synthesized TTS audio (`voiceover.mp3`) and SRT subtitles (`captions.srt`) are mixed in. The captions are styled using a customized subtitle filter (large centered font, white text, thick black border).

### B. LTX Text-to-Video Pipeline (`scripts/run_short_ltx.py`)
1. **Video Prompt Generation**: Groq returns `image_prompts` (which are detailed scene descriptions) rather than search queries.
2. **Video Generation via DeAPI**:
   - Iterates through the generated prompts, appending a preset's `image_style_suffix` (e.g. atmospheric lighting, photorealistic).
   - Calls `submit_video(prompt, client)` to POST the prompt to the DeAPI endpoint (`https://api.deapi.ai/api/v1/client/txt2video`) using the active Bearer token.
   - **Token Rotation & Limits**: The script maintains a pool of DeAPI keys (`DEAPI_TOKENS`). If a token encounters rate limits (HTTP 429) or billing issues (HTTP 400, 402, 422 with keywords like "credit" or "limit"), it prints a warning, increments the token index to rotate to the next token, and retries the submission.
   - **Status Polling**: Once submitted, it calls `poll_video` to request the job status from `https://api.deapi.ai/api/v1/client/request-status/<request_id>` every 5 seconds. Once completed, it fetches the raw `.mp4` video bytes from the returned `result_url` and writes them to disk.
3. **Video Processing & Stitching**:
   - Uses `get_video_duration` (via `ffprobe`) to detect the length of each clip.
   - Uses FFmpeg to preprocess each raw clip (scaling, cropping to 1080x1920, and shifting play speed via `setpts` so the clip duration matches the calculated timing window at 30fps).
   - Stitches clips together with xfade transitions and overlays subtitles, matching the audio length.

### C. FIFA Highlight Orchestrator (`scripts/fifa_orchestrator.py`)
1. **Video Source Scraping**:
   - Searches YouTube using `yt-dlp` for `"fifa 2026 highlights"`. It filters the top 20 search results to find a video with a duration between 3 and 60 minutes.
2. **AI Shorts Extraction**:
   - Runs a separate generator tool (`AI-Youtube-Shorts-Generator`'s `main.py`) as a subprocess: `python main.py '<video_url>' --num-clips 4 --aspect-ratio 9:16`.
   - This external tool splits the long video into 4 clips and writes metadata to a `result.json` file.
3. **Overlay & Synthesis**:
   - Reads `result.json` to find the path of each extracted clip.
   - Uses Groq to write a script based on the segment's viral hook metadata, synthesizes Edge TTS, generates captions SRT, and calls `render_video_background_short` in `pipeline/render_short.py` to overlay captions and voiceover directly onto the highlight clip.
4. **Slideshow Fallback**:
   - If the main highlight flow fails (due to YouTube IP blocking `yt-dlp` or parsing errors), the orchestrator catches the exception, overrides `sys.argv`, and imports `run_slideshow.py` to execute the image slideshow engine as a robust fallback.

---

## 3. Command-Line Inputs & Specification of Images

### A. Argument Analysis of Current Scripts
Currently, none of the entry points allow a user to directly specify image file paths or custom queries via CLI flags. They share a similar argparse structure:
* `--channel`: (Required/Default) Determines the target niche preset (e.g. `fifa_2026`, `football`, `football_history`).
* `--topic`: (Optional) Provides a topic hint for the LLM scriptwriter (e.g. `"Lionel Messi's World Cup trophy"`).
* `--upload`, `--instagram`, `--facebook`: (Optional flags) Controls whether to publish the rendered video to YouTube/Insta/FB.
* `--privacy`: (Optional) Sets video privacy to `private`, `unlisted`, or `public`.

Because the image retrieval is completely automated (the image prompts and search queries are generated programmatically by Groq based on the topic and presets), there is no entry point to pass local image files.

### B. Suggested CLI Extension for Testability and Customization
To facilitate E2E testing of the renderer without calling Groq or DDG search, and to support power users who want to compile shorts from local assets, we propose adding the following command-line flags to `run_slideshow.py` and `run_short_ltx.py`:
1. `--image-dir <path>`: Bypasses Groq script generation and DDG/DeAPI scraping entirely. The pipeline reads pre-existing images directly from this folder, scales them, and renders the slideshow.
2. `--image-queries <comma-separated-list>`: Overrides Groq-generated queries, forcing the script to search DDG for specific query strings provided by the user.

---

## 4. E2E Test Runner and Test Framework Design

We recommend establishing a `pytest`-based framework placed under `tests/` in the project root. This ensures tests are structured, easy to run, and leverage conftest fixtures.

### A. Proposed Directory Structure
```
/home/sp/Public/my_project/yt-automation/
├── tests/
│   ├── conftest.py                 # Core pytest mocks and fixtures
│   ├── assets/                     # Dummy media assets for fast test execution
│   │   ├── dummy_image.jpg         # 1x1 black pixel image (very small)
│   │   ├── dummy_audio.mp3         # 1-second silence MP3
│   │   └── dummy_video.mp4         # 1-second 1080x1920 MP4
│   └── e2e/
│       ├── test_run_short.py       # E2E checks for run_short.py
│       ├── test_run_short_ltx.py   # E2E checks for run_short_ltx.py
│       ├── test_run_slideshow.py   # E2E checks for run_slideshow.py
│       └── test_fifa_orchestrator.py # E2E checks for fifa_orchestrator.py
```

### B. Mocking Strategy for External Dependencies
To run E2E tests in a CODE_ONLY network mode without calling external APIs, we can mock out the underlying client objects and operations in `tests/conftest.py`:

1. **Groq API Client**:
   Mock the `groq.Groq` client constructor and its chat completion interface. Return standard JSON structures that match the expected output schemas:
   ```python
   # Mocking Groq response structure
   class MockChatCompletion:
       def __init__(self, content):
           self.choices = [type("Choice", (object,), {"message": type("Message", (object,), {"content": content})})]

   @pytest.fixture(autouse=True)
   def mock_groq(monkeypatch):
       mock_single_response = {
           "youtube_title": "Test Title",
           "youtube_description": "Test Desc #Shorts",
           "full_narration": "This is a mock narration that has enough words to pass the validation check.",
           "image_prompts": ["scene description one", "scene description two"],
           "visual_search_queries": ["test search query one", "test search query two"]
       }
       def mock_create(*args, **kwargs):
           return MockChatCompletion(json.dumps(mock_single_response))
       
       monkeypatch.setattr("groq.resources.chat.completions.Completions.create", mock_create)
   ```

2. **DuckDuckGo Image Scraping (`ddgs`)**:
   Intercept image downloads by mocking `fetch_web_image` or the `ddgs` class. The mock will copy a local dummy image instead of making HTTP requests:
   ```python
   @pytest.fixture(autouse=True)
   def mock_ddg_fetch(monkeypatch):
       def mock_fetch(query, out_path):
           # Copy local dummy asset to simulate successful download
           dummy_src = Path(__file__).parent / "assets" / "dummy_image.jpg"
           shutil.copyfile(dummy_src, out_path)
           return "ok", "mocked_url_of_image.jpg"
       monkeypatch.setattr("pipeline.web_images.fetch_web_image", mock_fetch)
   ```

3. **DeAPI Video Generation**:
   Mock the token rotation and polling logic in `run_short_ltx.py` to prevent network calls and write a dummy `.mp4` clip:
   ```python
   @pytest.fixture(autouse=True)
   def mock_deapi_video(monkeypatch):
       def mock_submit(prompt, client):
           return "mocked_req_123", "mocked_token_abc"
       def mock_poll(request_id, token, client, max_polls=150):
           # Return content of our 1-second dummy video
           dummy_vid = Path(__file__).parent / "assets" / "dummy_video.mp4"
           return dummy_vid.read_bytes()
           
       monkeypatch.setattr("scripts.run_short_ltx.submit_video", mock_submit)
       monkeypatch.setattr("scripts.run_short_ltx.poll_video", mock_poll)
   ```

4. **Edge TTS Synthesis**:
   Mock the `synthesize_full` function to output a dummy audio file and fake timings:
   ```python
   @pytest.fixture(autouse=True)
   def mock_tts(monkeypatch):
       def mock_synth(text, audio_path, voice=None):
           # Copy dummy audio asset
           dummy_audio = Path(__file__).parent / "assets" / "dummy_audio.mp3"
           shutil.copyfile(dummy_audio, audio_path)
           # Return a fixed duration and sentence timings list
           return 5.0, [{"start": 0.0, "end": 5.0, "word": "dummy text"}]
       monkeypatch.setattr("pipeline.edge_tts_synth.synthesize_full", mock_synth)
   ```

5. **Subprocess (FFmpeg & Uploads)**:
   - For E2E validation of FFmpeg command formatting, we can either verify the arguments passed to `subprocess.run` by mocking it, or execute the actual `ffmpeg` binary on the extremely short dummy media assets to verify that it completes successfully without wasting CPU.
   - Mock upload methods (`pipeline.youtube_upload.upload_short`, etc.) to prevent posting videos to live channels:
     ```python
     @pytest.fixture(autouse=True)
     def mock_uploads(monkeypatch):
         monkeypatch.setattr("pipeline.youtube_upload.upload_short", lambda *a, **k: "mocked_yt_id")
         monkeypatch.setattr("pipeline.instagram_upload.publish_instagram_reel", lambda *a, **k: "mocked_ig_id")
         monkeypatch.setattr("pipeline.instagram_upload.publish_facebook_reel", lambda *a, **k: "mocked_fb_id")
     ```

---

## 5. Structured 4-Tier E2E Test Suite Recommendations

We recommend dividing the test runner into 4 tiers to balance coverage, edge-case safety, complex flow interaction, and real-world execution.

### Tier 1: Feature Coverage (Component Integration)
* **Goal**: Validate that all parts of a single pipeline integrate correctly under default inputs.
* **Test Cases**:
  1. `test_slideshow_pipeline_flow`: Runs the slideshow generation with a standard channel niche preset. Confirms that a `short.mp4`, `voiceover.mp3`, and `captions.srt` are generated inside the output run directory with correct properties.
  2. `test_ltx_video_pipeline_flow`: Validates the text-to-video pipeline. Confirms raw clips are successfully preprocessed (scaled/cropped/speed-adjusted) and stitched together.
  3. `test_bilingual_variant_flow`: Runs `run_short.py` using a preset that has bilingual variants (e.g. `variants` list containing English and Hindi). Confirms that images are downloaded only once (shared) and that separate `short_en.mp4` and `short_hi.mp4` are generated with their respective voiceovers and fonts.

### Tier 2: Boundary & Error Handling
* **Goal**: Confirm the system handles API errors, bad formatting, resource constraints, and exceptions gracefully.
* **Test Cases**:
  1. `test_groq_invalid_json_fallback`: Mocks Groq to return invalid/malformed JSON or JSON missing required keys (e.g. no `full_narration` or empty image prompts). Checks that the script-generation retry loop triggers and eventually throws a clean error if it fails 3 times.
  2. `test_ddg_image_search_empty_fallback`: Mocks DuckDuckGo search to return 0 results. Validates that the fallback logic copies the previous image. If all fail, confirms it raises a clear exit error instead of crashing.
  3. `test_deapi_token_rotation`: Mocks the DeAPI endpoints to return HTTP 429 (rate limit) or HTTP 402 (payment required) on the first 3 tokens, and success on the 4th token. Verifies that `submit_video` successfully rotates through the token array and completes the submission without error.
  4. `test_deapi_tokens_exhausted`: Mocks DeAPI to return HTTP 401 (invalid credentials) for all configured tokens. Verifies that the script halts with a `RuntimeError` stating that all tokens are exhausted.
  5. `test_ffmpeg_not_installed`: Mocks `shutil.which("ffmpeg")` to return `None`. Verifies that `render_vertical_short` raises a `RuntimeError` explaining that ffmpeg is missing.

### Tier 3: Cross-Feature Interactions
* **Goal**: Test interactions between distinct modules and cross-cutting concerns.
* **Test Cases**:
  1. `test_fifa_orchestrator_scraper_failure_fallback`: Mocks `search_fifa_video` or `yt-dlp` in `fifa_orchestrator.py` to raise a `RuntimeError` (simulating YouTube IP blocking). Verifies that the orchestrator catches the error, overrides arguments, invokes the slideshow fallback (`run_slideshow.main`), and successfully renders the video using the alternative engine.
  2. `test_run_concurrency_safety`: Runs two pipeline invocations concurrently with the same channel ID. Verifies that because folders are generated using unique timestamps and UUIDs, they write to separate directories under `output/runs/` without overriding each other's temporary rendering assets or scripts.

### Tier 4: Real-world / End-to-End Simulation
* **Goal**: Validate the CLI entry points, folder routing, logging, and environment variables exactly as they would run in production/CI.
* **Test Cases**:
  1. `test_cli_invocation_via_subprocess`: Runs `python scripts/run_slideshow.py --channel football --topic "Real Madrid UCL"` using python's `subprocess.run` (with mocked APIs enabled via a test environment variable flag). Parses the CLI output to confirm print formatting, exit codes (0), and run folder creation.
  2. `test_history_json_logging`: Executes the pipeline and asserts that a history record is appended to `output/history/<channel>.json` with the title and summary returned from Groq, and that it maintains the `MAX_HISTORY` limit.
  3. `test_manual_upload_directory_routing`: Disables `--upload` in the CLI call and verifies that the final `.mp4` is successfully routed and copied to the `upload yt/` directory with a sanitized title filename (e.g. `Test_Title_en.mp4`).

---

## 6. Implementation Blueprint for the Implementer

The implementer can follow these steps to implement the test runner:

### Step 1: Create the Test Framework Structure
Create the directories and a `conftest.py` with mock setups:
```bash
mkdir -p tests/e2e tests/assets
touch tests/conftest.py
```
Create very small dummy files in `tests/assets` (e.g. a small jpg, a 1-second mp3 silence, and a small mp4 file) to avoid performance lag during test execution.

### Step 2: Write `tests/e2e/run_e2e_tests.py`
Provide a central Python script to invoke pytest with standard options:
```python
# tests/e2e/run_e2e_tests.py
import pytest
import sys

def main():
    # Run pytest on the e2e folder, reporting verbose output and stdout
    sys.exit(pytest.main(["-v", "-s", "tests/e2e"]))

if __name__ == "__main__":
    main()
```

### Step 3: Implement Mocks and Fixtures in `conftest.py`
Ensure all external boundaries are stubbed out as shown in Section 4. B, using pytest fixtures to isolate tests from the live network.

### Step 4: Write the E2E Test Cases
Implement the 4-tier E2E tests in their respective files (e.g., `tests/e2e/test_run_slideshow.py`). For example, a basic E2E test:
```python
# tests/e2e/test_run_slideshow.py
import pytest
from scripts import run_slideshow

def test_run_slideshow_e2e(monkeypatch, tmp_path):
    # Mock REPO_ROOT to avoid cluttering actual output dirs
    monkeypatch.setattr("scripts.run_slideshow.REPO_ROOT", tmp_path)
    
    # Simulate arguments
    class Args:
        channel = "football"
        topic = "Mock Topic"
        upload = False
        instagram = False
        facebook = False
        privacy = "private"
        
    # Execute the slideshow pipeline
    # (Because the APIs are mocked globally in conftest.py, this will run offline)
    run_slideshow.main()
    
    # Assert expected outputs are generated
    runs_dir = tmp_path / "output" / "runs"
    assert runs_dir.exists()
    run_folders = list(runs_dir.iterdir())
    assert len(run_folders) == 1
    
    run_folder = run_folders[0]
    assert (run_folder / "script.json").exists()
    assert (run_folder / "voiceover.mp3").exists()
    assert (run_folder / "captions.srt").exists()
    assert (run_folder / "short.mp4").exists()
```

### Step 5: Test Execution and Verification
Verify that the tests can be run locally using the standard test command:
```bash
pytest tests/
```
Or via the Python runner:
```bash
python tests/e2e/run_e2e_tests.py
```
