# E2E Test Infra: yt-automation

## Test Philosophy
- Opaque-box, requirement-driven. No dependency on implementation design.
- Methodology: Category-Partition + BVA + Pairwise + Workload Testing.

## Feature Inventory
| # | Feature | Source (requirement) | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---|---|---|:---:|:---:|:---:|:---:|
| F1 | Input manual image URLs | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| F2 | Download manual images | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| F3 | Generate video from manual images | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| F4 | Fallback to automatic image generation | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |

## Test Architecture
- **Test Runner**: Python-based runner located at `tests/e2e/run_e2e_tests.py` using `pytest`.
- **Invocation**: `python tests/e2e/run_e2e_tests.py --tier <1/2/3/4/all> --mode <mocked/live>`
- **Pass/Fail Semantics**: 
  - Exit code 0 indicates all tests passed.
  - Non-zero indicates failure.
- **Directory Layout**:
  ```
  tests/
  ├── conftest.py
  ├── assets/
  │   ├── dummy_image.jpg
  │   ├── dummy_audio.mp3
  │   └── dummy_video.mp4
  └── e2e/
      ├── run_e2e_tests.py
      ├── test_manual_input.py
      ├── test_download.py
      ├── test_video_gen.py
      └── test_fallback.py
  ```

## Test Case Inventory

### Tier 1 - Feature Coverage (Functional Verification)
* **F1: Input manual image URLs**
  * `test_t1_f1_cli_urls_ltx`: Comma-separated URLs passed via CLI input to `run_short_ltx.py`.
  * `test_t1_f1_cli_urls_slideshow`: Comma-separated URLs passed via CLI input to `run_slideshow.py`.
  * `test_t1_f1_file_urls`: File path input for URLs list.
  * `test_t1_f1_env_urls`: Environment variable input for URLs list.
  * `test_t1_f1_json_urls`: JSON formatted URLs passed via CLI/env.
* **F2: Download manual images**
  * `test_t1_f2_download_jpeg`: Download multiple valid JPEGs successfully.
  * `test_t1_f2_download_png`: Download multiple valid PNGs successfully.
  * `test_t1_f2_download_webp`: Download multiple valid WebPs successfully.
  * `test_t1_f2_download_mixed`: Download combinations of different valid image formats.
  * `test_t1_f2_user_agent`: Verify custom User-Agent is sent to bypass blocks.
* **F3: Generate video from manual images**
  * `test_t1_f3_video_output`: Verify video output file exists and has non-zero size.
  * `test_t1_f3_video_aspect_ratio`: Verify video aspect ratio is exactly vertical 9:16.
  * `test_t1_f3_video_transitions`: Verify video contains crossfades/transitions between manual images.
  * `test_t1_f3_video_codec`: Verify video codec is h264.
  * `test_t1_f3_audio_track`: Verify audio track is AAC.
* **F4: Fallback to automatic image generation**
  * `test_t1_f4_no_urls_ltx`: Fallback to auto-generation when no manual URLs are provided to `run_short_ltx.py`.
  * `test_t1_f4_no_urls_slideshow`: Fallback to auto-generation when no manual URLs are provided to `run_slideshow.py`.
  * `test_t1_f4_download_fail_fallback`: Manual URLs fail to download, falls back to automatic search.
  * `test_t1_f4_workflow_empty_daily`: Workflow input is empty string in daily short run (falls back to auto).
  * `test_t1_f4_workflow_empty_slideshow`: Workflow input is empty string in slideshow run (falls back to auto).

### Tier 2 - Boundary & Corner Cases
* **F1: Input manual image URLs**
  * `test_t2_f1_empty_urls_input`: Empty URLs list input (triggers fallback).
  * `test_t2_f1_urls_whitespace`: URLs containing excessive whitespace.
  * `test_t2_f1_large_url_list`: Extremely long URL lists (boundary testing).
  * `test_t2_f1_malformed_urls`: URLs missing `http` or `https` prefix.
  * `test_t2_f1_duplicate_urls`: Duplicate URLs in input list.
* **F2: Download manual images**
  * `test_t2_f2_http_404_error`: Download fails with HTTP 404.
  * `test_t2_f2_http_403_error`: Download fails with HTTP 403.
  * `test_t2_f2_magic_byte_fail`: Download returns HTML content instead of image.
  * `test_t2_f2_download_timeout`: Download timeout.
  * `test_t2_f2_partial_download_fail`: Part-download failure (some succeed, others fail).
* **F3: Generate video from manual images**
  * `test_t2_f3_single_image`: Generate video with only 1 manual image (minimum boundary).
  * `test_t2_f3_max_images`: Generate video with maximum supported images (e.g. 50 images).
  * `test_t2_f3_size_mismatch`: Generate video where input image sizes are mismatched.
  * `test_t2_f3_corrupted_image`: Generate video where an image is corrupted on disk.
  * `test_t2_f3_fps_override`: Generate video with custom frame rate overrides.
* **F4: Fallback to automatic image generation**
  * `test_t2_f4_all_downloads_fail`: All manual image downloads fail, falls back to automatic generation.
  * `test_t2_f4_partial_download_fallback`: Partial URL download failures are filled via auto-generation.
  * `test_t2_f4_empty_fallback_queries`: Fallback search queries are empty.
  * `test_t2_f4_zero_results_fallback`: Fallback search queries return zero results.
  * `test_t2_f4_successful_fallback_render`: Fallback occurs and video generator runs successfully.

### Tier 3 - Cross-Feature Combinations (Pairwise Coverage)
* `test_t3_partial_fail_and_fallback`: Manual URLs input + partial download failure + fallback to auto-generation.
* `test_t3_token_rotation_and_manual`: Manual URLs input + DeAPI token rotation during video generation.
* `test_t3_bilingual_and_manual`: Manual URLs input + dual bilingual rendering + upload trigger.
* `test_t3_ddg_mock_and_watermark`: Manual URLs input + DuckDuckGo search mock + watermark removal execution.

### Tier 4 - Real-World Application Scenarios
* `test_t4_e2e_manual_ltx`: End-to-End YouTube Short Generation with Manual URLs.
* `test_t4_e2e_manual_slideshow`: End-to-End Slideshow Generation with Manual URLs.
* `test_t4_workflow_daily_short`: GitHub Actions `daily_short.yml` workflow run simulation.
* `test_t4_workflow_slideshow`: GitHub Actions `slideshow.yml` workflow run simulation.
* `test_t4_fifa_scrape_fallback`: Robust fallback from video scraping failure in `fifa_orchestrator.py` to slideshow with manual URLs.

## Coverage Thresholds
- Tier 1: ≥5 per feature (20 total)
- Tier 2: ≥5 per feature (20 total)
- Tier 3: pairwise coverage of major feature interactions (4 total)
- Tier 4: ≥5 realistic application scenarios (5 total)
- **Total Minimum: 49 test cases**
