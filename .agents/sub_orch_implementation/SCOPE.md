# Scope: Implementation Track

## Architecture
- Workflows: `.github/workflows/daily_short.yml`, `.github/workflows/slideshow.yml`
- Scripts: `scripts/run_short.py`, `scripts/run_short_ltx.py`, `scripts/run_slideshow.py`
- Core logic:
  - Download helper to retrieve image URLs using standard python `urllib.request`.
  - Handle image/video generation bypass when manual URLs are provided.
  - Integration with GitHub Action workflow inputs.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Exploration & Design | Explorer analyzes codebase, verifies script inputs, and recommends detailed design | None | DONE |
| 2 | Script Modification | Worker implements manual URL downloading/processing in run_short.py, run_short_ltx.py, and run_slideshow.py; Reviewer verifies | M1 | DONE |
| 3 | Workflow & E2E Testing | Worker modifies workflows to accept image_urls input; run E2E tests, fix failures, perform Forensic Audit and Tier 5 hardening | M2 | IN_PROGRESS |

## Interface Contracts
### CLI Arg: `--image-urls`
- Option: `--image-urls`
- Type: string (comma-separated list of URLs)
- Behavior:
  - If provided, download the images to the run's image directory (e.g. `scene_01.png`, etc.).
  - Bypass DeAPI image/video generation and web scraping.
  - For `run_short_ltx.py`, convert the downloaded static images into short video clips using FFmpeg so the rest of the pipeline is preserved.
  - For `run_short.py` and `run_slideshow.py`, use the downloaded images directly.
  - If not provided, fall back to the default image/video generation.
