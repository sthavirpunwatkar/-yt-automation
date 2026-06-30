# Orchestrator Execution Plan: YouTube Shorts Manual Images Support

This plan details the steps to modify the YouTube Shorts generation pipeline to support manually provided images instead of auto-generating them, ensuring fallback behavior when no manual URLs are provided.

## Workflow & Verification Strategy
We use the **Project Orchestration Pattern** with a Dual Track (Testing and Implementation) and strict verification gates.

## Steps

### Step 1: Initialization and Planning
- [x] Create `ORIGINAL_REQUEST.md` to capture user goals.
- [x] Create `BRIEFING.md` with system constraints and team role mappings.
- [x] Define `PROJECT.md` at orchestrator root with milestones and interface contracts.
- [x] Create `progress.md` to track liveness and task updates.
- [x] Write `plan.md` (this file).

### Step 2: E2E Testing Track (Milestone 1)
- [ ] Spawn **E2E Testing Orchestrator** subagent to build the test suite independently from implementation.
- [ ] Identify features from requirements:
  - Feature 1: Manual image URL parsing from CLI/workflows.
  - Feature 2: Downloading images locally.
  - Feature 3: Video construction from downloaded images.
  - Feature 4: Fallback behavior to auto-generation when no manual URLs are provided.
- [ ] Build Tier 1-4 tests:
  - Tier 1: Feature coverage (e.g. test parsing, downloading, video generation with dummy image URLs).
  - Tier 2: Boundary/edge cases (e.g. empty URLs, invalid URLs, mismatch in count of scenes vs URLs, large image files).
  - Tier 3: Cross-feature combinations (e.g. mix of manual URLs and default behavior, if applicable).
  - Tier 4: Real-world workloads (e.g. full end-to-end execution generating a real short using a list of valid test image URLs).
- [ ] Create test harness and runner.
- [ ] Publish `TEST_READY.md` containing the test command and coverage summary.

### Step 3: Implementation Track (Milestone 2)
- [ ] Spawn **Implementation Orchestrator** subagent.
- [ ] Analyze codebase to understand:
  - How scripts (`scripts/run_short_ltx.py`, `scripts/run_short.py`, `scripts/run_slideshow.py`, etc.) generate/retrieve images.
  - How moviepy/ffmpeg constructs videos from those images.
  - How GitHub Actions workflows invoke these scripts.
- [ ] Implement command line argument `--image-urls` in the Python scripts.
- [ ] Implement image downloading mechanism with appropriate local paths.
- [ ] Modify video construction code to use downloaded image files.
- [ ] Add input parameters to GitHub Action workflow files (`daily_short.yml`, `slideshow.yml`, etc.) and pass them to the scripts.
- [ ] Verify that default behavior (without manual URLs) remains unaffected.
- [ ] Run the E2E tests and debug until all pass.
- [ ] Run Forensic Audit on the final implementation to verify integrity.

### Step 4: Verification and Reporting
- [ ] Synthesize test results and reviewer/challenger/auditor feedback.
- [ ] Verify that final layout matches `PROJECT.md`.
- [ ] Report final completion status to parent agent.
