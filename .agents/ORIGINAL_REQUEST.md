# Original User Request

## Initial Request — 2026-06-30T13:55:56Z

# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview

Update the YouTube Shorts generation pipeline to support manually provided images instead of auto-generating them, to avoid copyright issues. The GitHub Actions workflows should accept a list of image URLs, which the generation script will download and use to compose the video.

Working directory: /home/sp/Public/my_project/yt-automation
Integrity mode: development

## Requirements

### R1. Image URL Input
Modify the GitHub Action workflows (e.g., `daily_short.yml`) to accept an optional input for a list of direct image URLs (e.g., as a comma-separated string or a text payload).

### R2. Script Modification
Update the underlying video generation script (like `scripts/run_short_ltx.py`) so it accepts the provided image URLs, downloads them locally, and uses them to construct the final video.

### R3. Fallback/Default Behavior
Ensure the scripts still work (or gracefully error) when no manual URLs are provided.

## Acceptance Criteria

### Workflow Changes
- [ ] The GitHub Action workflow can be manually triggered with an input for image URLs.

### Script Execution
- [ ] The Python script parses the image URLs correctly.
- [ ] The script successfully downloads the provided images from the internet.
- [ ] The script successfully generates a video file using the downloaded images without rendering errors.
