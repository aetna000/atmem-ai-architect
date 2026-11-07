# Plan

1. Establish a reusable seven-scenario catalog and live browser validation runner.
2. Run small real-model baselines through the normal UI and archive artifacts.
3. Fix observed generator/workflow failures with deterministic regression tests; rerun affected scenarios.
4. Qualify the simplest generated deployment in AWS once account, region and cost envelope are confirmed.
5. Expand native implementations only through reviewed, bounded scenario inputs; continue through the ladder.

Constitution check: user-controlled changes and deployment; no invented evidence; project-driven artifacts; local credential chain; limited verified provider coverage; isolated test memory; normal UI; regression tests.

## Clarified priority — product qualification first

The user explicitly prioritizes repeated prompt → diagram → Terraform → evaluation → product/skill fix → rerun cycles. Do not move directly from credentials or Terraform schema validation to deployment. Use bounded multi-turn runs with preserved artifacts. Classify missing native implementations separately from model diagram errors. Do not invent success percentages or hide unchanged failures. Only a candidate with complete implementation and reviewed evidence proceeds to account planning and then an end-to-end deployment test.
