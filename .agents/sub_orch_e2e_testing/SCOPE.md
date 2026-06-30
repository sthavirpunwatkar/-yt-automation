# Scope: E2E Testing Track

## Architecture
- **Test Runner**: A Python-based E2E test runner (`tests/e2e/run_e2e_tests.py`) that runs tests, mocks HTTP downloads if needed, checks script execution output/exit codes, and verifies video file characteristics.
- **Mock Server / Assets**: Local HTTP server or mock endpoints for testing image downloads under offline/controlled environments.
- **Test Categories**: Separated directories or test classes for each of the 4 tiers (Tier 1: Feature, Tier 2: Boundary, Tier 3: Pairwise, Tier 4: Workloads).

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| 1 | E2E Test Infra | Design test runner, mock server, directory structures | None | DONE |
| 2 | Tier 1 Tests | Implement Tier 1 (Feature Coverage) test cases (20 tests) | M1 | DONE |
| 3 | Tier 2 Tests | Implement Tier 2 (Boundary & Corner Cases) test cases (20 tests) | M2 | DONE |
| 4 | Tier 3 & 4 Tests | Implement Tier 3 (Cross-Feature Combinations) and Tier 4 (Real-world Application Scenarios) test cases (10 tests) | M3 | DONE |
| 5 | Verification & Audit | Run all tests, perform review and forensic audit, publish TEST_READY.md | M4 | IN_PROGRESS |

## Interface Contracts
### E2E Test Runner ↔ YouTube Shorts Scripts (`scripts/run_short_ltx.py` / `scripts/run_slideshow.py`)
- CLI execution via `subprocess.run`.
- Input parameters: `--image-urls` (comma-separated string or file path).
- Expected outputs: Exit codes (0 for success, non-zero for failure), log messages, and generated video files.
