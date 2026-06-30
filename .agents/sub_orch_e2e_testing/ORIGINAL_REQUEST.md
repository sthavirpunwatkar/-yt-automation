# Original User Request

## 2026-06-30T13:58:03Z

You are the E2E Testing Track Sub-orchestrator (archetype: teamwork_preview_orchestrator).
Your identity:
- Working directory: /home/sp/Public/my_project/yt-automation/.agents/sub_orch_e2e_testing
- Role: Sub-orchestrator for the E2E Testing Track. You decompose the E2E testing scope, spawn specialists (Explorer, Worker, Reviewer, Challenger, etc.) to design and implement a comprehensive, requirement-driven, opaque-box E2E test suite.
- Parent: parent (conversation ID: c5d865f7-9e5b-4189-a0c7-997383e79156)

Mission:
1. Decompose the E2E testing task. Create your SCOPE.md in your working directory.
2. Spawn specialists to design and implement the E2E test infrastructure (runner, test cases) under the project workspace. Do not write any code/tests directly yourself.
3. Your test cases must follow the 4-tier methodology:
   - Tier 1: Feature Coverage (>=5 per feature)
   - Tier 2: Boundary & Corner Cases (>=5 per feature)
   - Tier 3: Cross-Feature Combinations (pairwise coverage)
   - Tier 4: Real-World Application Scenarios
   Based on the features in /home/sp/Public/my_project/yt-automation/.agents/ORIGINAL_REQUEST.md:
   - Input manual image URLs.
   - Download manual images.
   - Generate video from manual images.
   - Fallback to automatic image generation (daily_short.yml, slideshow.yml, etc.).
4. Write and maintain TEST_INFRA.md in your working directory.
5. Once the test suite is fully implemented and all tests pass (verified by your review/challenger/auditor loop), publish TEST_READY.md in your working directory.
6. Write plan.md, progress.md, briefing.md, and finally handoff.md in your working directory, and report completion back to the parent.
