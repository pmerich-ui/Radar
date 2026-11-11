# DealRadar Schweiz — Zero-CHF Video Provider Router (research branch)

**51 candidates:** 49 original entries (the previously stated figure 41 was a counting error) + Creative Claw + fal.ai. See [providers.json](providers.json). The catalogue is intentionally fail-closed: public terms are NOT an account authorization.

## Reproduce the read-only audit

```sh
python -m video_router.audit_cli
python -m unittest discover -s tests -v
```

- `catalog.py`: model-specific eligibility gate; blocks unknown/personal-only licenses, unknown free pricing, inaccessible APIs, unknown credit quotes, and unsupported 9:16/480p.
- `provider_router.py`: automatically tries the next **authorized and eligible** provider if the previous one fails; does not buy credits, bypass logins, remove watermarks, or publish.
- `verify_mp4.py`: ffprobe technical check on a **real locally downloaded** MP4, 15-20 seconds, vertical 9:16, at least 480p portrait equivalent, with an audio stream. Audible volume, Swiss German pronunciation, music license, 3-person dance continuity, and visual artifacts still require additional inspection.
- `audit_cli.py`: prints all provider blockers without connecting to third-party accounts.
- `free_fallback.py`: early prototype retained for history; **new integrations must use provider_router.py**, not legacy defaults.

## Status on November 11, 2026

- **Creative Claw:** 12 available credits, read-only estimated 5 seconds at 480p cost 15 credits (Seedance Mini) / 25 credits (MiniMax H3 Turbo). No generation attempted. Historic free-first-clip grant not assumed available.
- **Higgsfield:** 10 credits; one available free motion-control operation requiring source content, not pure text-to-video; free-trial not started.
- **Invideo:** 31.7 credits, commercial 15-20 second output entitlement not verified.
- **fal.ai:** generation account blocked because its balance is exhausted. Do not retry automatically or incur costs.
- **Leonardo.Ai, Runway, Adobe Firefly:** official text supports commercial use under particular conditions, but no authenticated free video quote or automatic generation adapter has been installed.
- **PixVerse, Pika, Krea, Luma, Freepik/Magnific, OpenArt:** free output not commercially licensed according to reviewed provider terms/plan descriptions; block for DealRadar ads.
- **Remaining providers:** unknown per-model terms and/or account-level credits. Open-source weights still need version-specific license and demonstrated 0-CHF GPU availability.

## Activation sequence

1. Register an **official authenticated generation adapter**. Do not automate website logins, CAPTCHA, quota evasion or paid APIs using an unofficial wrapper.
2. Fetch the exact model's commercial-use rights, actual account balance, free-credit reservation and free 9:16/480p ability **at invocation time**.
3. Only mark `READY` if additional CHF cost is provably zero and the request is eligible. Any unavailable or ambiguous price/licence is a hard skip.
4. Segment the 15-20s Alpine lake comedy brief into 5-8s source clips if needed; preserve the 3 adult dancers and synchronized choreography.
5. After each real provider response, verify actual media existence, download and check bytes; use idempotency keys and do not automatically resubmit ambiguous jobs.
6. Compose the finished video with separately licensed music and verified Swiss-German speech, inspect audible audio and visual realism, evaluate DealRadar quality threshold >=85/100.
7. Save privately for **manual approval only**; no social-media publishing.

**Not yet implemented:** live provider adapters, account OAuth, persistent retry ledger, voice/music generation, actual video montage and 85/100 audiovisual evaluator. This is a tested catalogue and policy/router foundation, NOT a deployed autonomous production system.


## Completed provider-by-provider screening (2026-11-11)

The full 51-entry table is `providers.json`. Breakdown: **45 public-official-plan/terms reviews, 5 connected ChatGPT-account checks, 1 unresolved official source (Kling AI)**. This is **not** 50 API integrations and does not certify every free output as commercial.

Potential free commercially licensed services (model- and export-specific eligibility still requires a real free-account quote): Leonardo.Ai, Runway, Adobe Firefly-owned models, Fotor, Vidnoz, Clipfly, SeaArt's specific SkyReels-V3 implementation, Canva's free 5-second image-to-video. For self-hosting: Wan 2.2 and Mochi 1, plus strictly Apache-2.0 CogVideoX-2B weights, but only if compute is actually free.

Known commercial blocks or restrictions include PixVerse, Pika, Krea, Luma, LTX Studio, Genmo free, Kaiber's paid trial, renderforest, HeyGen, OpenArt, Freepik and Pollo. Others are allowed into the research register but blocked from deployment until exact model permissions and account-level pricing are verified.

Connected-service snapshots (read-only, 2026-11-11):
- Creative Claw 12 credits; the verified low-cost 5-second 480p quote is 15 Seedance Mini credits or 25 MiniMax H3 Turbo credits; no affordable selected request.
- Higgsfield 10 credits and one free *motion-control* operation requiring source content; no pure text-to-video free model seen.
- Invideo 31.7 credits; full commercial export allowance unknown.
- VEED 50 AI Playground credits, available tool is talking-head avatars, not a general three-person cinematic scene generator.
- fal.ai connected account reports out-of-credits billing block; DO NOT retry, buy, or switch accounts.

**Important limitation:** `providers.json` lists prospective integrations; `automatic_adapter:false` for all 51. No authenticated callable zero-cost ad-video provider was installed in this branch. Unconnected browser sites cannot be automatically turned into APIs by listing them. Live provider selection will be possible only after approved official adapters and each current-account license/credit check are implemented.

The current audit is read-only and all providers are fail-closed without live proofs. CI / local tests, verified MP4 assets, audible Swiss German/music, quality scoring and production deployment must be checked independently. No video generation or publishing has been performed by this integration work.
