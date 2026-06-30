## 2026-06-30T19:32:10Z
Objective: Implement manual image URL downloading and processing in the script files.

Identity: worker_1
Working Directory: /home/sp/Public/my_project/yt-automation/.agents/worker_1

Refer to the design strategy in:
`/home/sp/Public/my_project/yt-automation/.agents/sub_orch_implementation/explorer_handoff.md`

Tasks:
1. Create a new file `pipeline/downloader.py` implementing `download_manual_images(urls_str: str, dest_dir: Path) -> list[Path]` using Python's standard `urllib.request`. The function must clean, parse, validate, download the URLs, and return a list of local file Path objects. Raise a RuntimeError if any download fails.
2. Modify `scripts/run_short.py` to:
   - Add `--image-urls` argument.
   - If `--image-urls` is provided, download URLs to `img_dir` using the helper, and bypass DeAPI image generation.
   - If not provided, fall back to default DeAPI generation.
3. Modify `scripts/run_short_ltx.py` to:
   - Add `--image-urls` argument.
   - If `--image-urls` is provided:
     - Download URLs to `vid_dir` using the helper.
     - Bypass DeAPI txt2video submission/polling.
     - For each image, convert it to a video clip of the required segment duration (`clip_dur = (total_dur + (n_clips - 1) * FADE_DUR) / n_clips` if `n_clips > 1` else `total_dur`) using FFmpeg (crop/scale to 1080x1920 at 30 fps, pix_fmt yuv420p, encoder libx264 or the dynamically selected encoder).
     - Store the processed clips in `processed_video_paths` directly to bypass the regular preprocessing step.
   - If not provided, fall back to default DeAPI txt2video generation.
4. Modify `scripts/run_slideshow.py` to:
   - Add `--image-urls` argument.
   - If `--image-urls` is provided, download URLs using the helper, bypass DuckDuckGo search, and use them directly for slideshow rendering.
   - If not provided, fall back to DuckDuckGo search.
5. Verify your changes by running each script in dry-run mode (e.g. with a test channel, or mock URLs, or without actually uploading to YouTube) to ensure they work without errors. Check the rendered output mp4.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Write your changes summary and local test outputs to `/home/sp/Public/my_project/yt-automation/.agents/worker_1/handoff.md`.
Reply with a completion message when done.
