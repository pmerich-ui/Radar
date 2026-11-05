# DealRadar Schweiz — autonomous operations mandate

Goal: generate three original, rights-cleared 9:16 short videos daily, and publish to @erco227 at 08:00, 13:00, 19:00 and @dy3ko4nveu0o at 10:00, 15:00, 21:00 Europe/Zurich, tracking each channel separately. Zero new paid subscriptions without explicit approval.

## Execution order
1. Inspect existing GitHub, Render, Val Town, Metricool, and TikTok/Buffer connections and actual video artifacts.
2. Preserve working infrastructure; change only what is required; run tests and inspect actual generated MP4s.
3. Use Metricool for its already-authorized channel. For @erco227, evaluate Buffer and official TikTok Content Posting API; use only officially supported OAuth authorization. Do not pretend a ChatGPT instruction grants platform permissions.
4. Obtain user action only when a third-party sign-in/OAuth confirmation is necessary. Do not request passwords, access tokens, or paid upgrades.
5. Before any public posting: verify actual account authorization, rights and content, quality checks, duplicate suppression, platform eligibility and successful end-to-end test. User has expressed intent to authorize a controlled test, but do not claim an upload without provider confirmation.
6. Publish and persist unique platform post IDs; distinguish scheduled from published. Measure views separately from clicks and commissions. Never claim revenue without verified affiliate data.
7. Fail closed, retry transient failures safely, avoid duplicate posts, preserve privacy and costs.

## Status as of 2026-11-05
- @dy3ko4nveu0o connected via Metricool brand 7820933.
- @erco227 user is onboarding Buffer; OAuth/channel connection is NOT verified.
- Dual-channel time plan saved in config/tiktok_channels.json; publishing disabled.
- Producer code changed to 1080x1920, 18 seconds; rendered file and full decode audit not yet confirmed.
- Val Town click event API was tested; live end-to-end browser click remains unverified.

## Operating rule
Autonomy means execute all accessible actions without repeated permission requests, but never bypass OAuth, security controls, external confirmations, platform requirements, or cost approvals. Report only confirmed results.
