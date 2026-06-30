# E2E Testing Track Plan

## Goal
Implement a robust, 4-tier E2E testing suite for the manual image feature in the YouTube Shorts generation pipeline, and verify the implementation via Reviewer, Challenger, and Forensic Auditor loop.

## Phase 1: Test Design & Infrastructure (Milestone 1)
1. Spawn Explorer to investigate the codebase:
   - Identify inputs, script entry points, and video rendering logic.
   - Inspect `scripts/run_short_ltx.py`, `scripts/run_slideshow.py`, and the GitHub Action workflows.
   - Identify how images are downloaded and processed.
2. Draft `TEST_INFRA.md` outlining the test runner, features, and test case inventory.
3. Spawn Worker to create the E2E test runner (`tests/e2e/run_e2e_tests.py`), directories, and mock assets.

## Phase 2: Test Implementation (Milestones 2, 3, 4)
1. Spawn Worker to implement Tier 1 Feature Coverage tests (5 tests per feature, total 20 tests).
2. Spawn Worker to implement Tier 2 Boundary & Corner cases (5 tests per feature, total 20 tests).
3. Spawn Worker to implement Tier 3 (Cross-feature pairwise combinations) and Tier 4 (Real-world scenarios) tests (total 10 tests).

## Phase 3: Verification & Execution (Milestone 5)
1. Spawn Reviewers to inspect test implementation correctness and completeness.
2. Spawn Challengers to verify correctness and robustness.
3. Spawn Forensic Auditor to perform integrity audit on the tests and code.
4. If all tests pass and verification succeeds, publish `TEST_READY.md`.

## Phase 4: Closure
1. Compile final handoff report (`handoff.md`).
2. Message parent with completion status.
