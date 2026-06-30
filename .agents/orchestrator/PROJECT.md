# Project: yt-automation-manual-images

## Architecture
- The pipeline generates YouTube Shorts and slideshows.
- GitHub Action workflows (e.g., `.github/workflows/daily_short.yml`) trigger Python scripts in the `scripts/` directory (e.g., `scripts/run_short_ltx.py`).
- The scripts coordinate content generation, image asset retrieval/generation (via `pipeline/images.py` or similar), audio synthesis, and video rendering using moviepy/ffmpeg.
- We need to introduce an optional input for manual image URLs in the workflows and modify the scripts to parse, download, and construct videos from these manual URLs instead of auto-generating them.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | E2E Testing Track | Define requirements, design test harness/cases, publish TEST_READY.md | None | IN_PROGRESS (Conv ID: 1bf10495-749f-4158-af61-0bbf4bac8457) |
| 2 | Implementation Track | Modify scripts and workflows to support manual image URLs, verify with test suite | M1 | IN_PROGRESS (Conv ID: 4ddf1d2b-e6c9-4164-ae0e-f6155c53a7e8) |

## Interface Contracts
### GitHub Actions Workflows ↔ Video Generation Scripts
- The workflows run the python scripts via command-line arguments.
- We will add an optional command-line argument `--image-urls` to the scripts, which accepts a comma-separated list of image URLs.
- The workflows will pass the workflow input `image_urls` (if provided) to the scripts via the `--image-urls` argument.
- If `--image-urls` is provided, the script skips automatic image generation, downloads the URLs, and uses the downloaded image files as scene assets. If downloading fails, it should report a clear error and exit/fallback.
- If `--image-urls` is not provided, the script falls back to its existing behavior (generating images using the configured generator, e.g. Sketch, LTX, etc.).

## Code Layout
- `.github/workflows/` - GitHub Actions workflow definition files
- `scripts/` - Entrypoint Python scripts for video/slideshow generation
- `pipeline/` - Core logic files (image generation, rendering, captioning, etc.)
