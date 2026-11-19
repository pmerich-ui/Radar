# DealRadar: P0 integration status (17 Nov 2026)

**This is an integration staging branch, not a deployment.** No publishing is enabled.

## Received external patch

The locally supplied `radar_fix(1).zip` contains a separate ledger, upload guard, Awin validator, video QA, test suite and workflow template. Its 35 tests pass locally after explicitly closing SQLite connections. **The patch is not yet merged into this repository** because `src/production_ledger.py` already exists on PR #5 and uses an incompatible state machine.

## Required merge decisions

1. Choose one canonical ledger schema and state machine. Do not replace PR #5's ledger blindly.
2. Add explicit database connection lifecycle and real PostgreSQL concurrent integration tests.
3. Enforce the upload guard around the *actual* Metricool API call, not only around a dummy callback.
4. Confirm whether Metricool supports lookup by SHA-256/idempotency metadata; otherwise ambiguous uploads must remain blocked.
5. Verify Awin merchant approvals, feed columns, tracking domains, CHF prices and offer freshness using real data.
6. Ensure platform visibility is validated against actual TikTok host and public post evidence.
7. Keep per-video owner approval mandatory before publishing. A CI score is not approval.
8. Run one fully evidenced end-to-end test before enabling schedules; then measure 21/21 over 7 days.

## Current production status

No Supabase credentials or database self-test were provided for this integration. No verified Awin offer or new TikTok URL is evidenced by the supplied patch. No schedule or auto-publishing change is authorized by this document.
