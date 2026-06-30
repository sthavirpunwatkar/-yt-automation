## 2026-06-30T14:08:22Z

Objective: Modify GitHub workflows daily_short.yml and slideshow.yml to support manual image URLs.

Identity: worker_2
Working Directory: /home/sp/Public/my_project/yt-automation/.agents/worker_2

Tasks:
1. Modify `.github/workflows/daily_short.yml` to:
   - Expose a new input parameter `image_urls` (type string, description: "Comma-separated list of manual image URLs", required: false, default: "").
   - Update the "Generate & upload Short" step to retrieve the `image_urls` input and pass it as `--image-urls "$IMAGE_URLS"` to `scripts/run_short_ltx.py` if not empty.
2. Modify `.github/workflows/slideshow.yml` to:
   - Expose a new input parameter `image_urls` (type string, description: "Comma-separated list of manual image URLs", required: false, default: "").
   - Update the "Run Slideshow Engine" step to retrieve the `image_urls` input and pass it as `--image-urls "$IMAGE_URLS"` to `scripts/run_slideshow.py` if not empty.
3. Verify that both files are valid YAML.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Write a summary of changes and verification to `/home/sp/Public/my_project/yt-automation/.agents/worker_2/handoff.md`.
Reply with a completion message when done.
