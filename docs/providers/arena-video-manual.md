# Arena Video -> DealRadar Schweiz (manual provider, fail-closed)

Status: **MANUAL_ONLY / NOT AUTOMATED / NOT RIGHTS_CLEARED**. This document is an integration contract, not evidence of an Arena API connection or completed generation.

## Verified source references
- https://help.arena.ai/articles/1544829667-how-to-create-videos-with-video-arena
- https://help.arena.ai/articles/5629909088-terms-of-use
- https://arena.ai/blog/video-arena
- https://platform.arena.ai/terms

Arena Video web uses Battle mode, requires login, typically produces 5-8 second clips, and (per help page) limits use to two generation requests per 24h; availability may change. The website terms prohibit programmatic/automated queries. The separate Arena API preview is **not** verified to provide free commercial video generation.

## Operator workflow (no automatic browser requests)
1. User manually opens https://arena.ai/video, signs in, selects Video and pastes an original Swiss-comedy prompt (max UI length as displayed).
2. User downloads the resulting video(s) through the Arena UI, without automation or scraping. Do not bypass quotas.
3. Before commercial use, explicitly verify rights for the Arena output AND underlying model, account tier, and any audio/music/likeness. If uncertain, mark `RIGHTS_UNVERIFIED`; no publication.
4. Put the downloaded file in the existing DealRadar video intake/production flow. Never assume Arena's short clip is a 15-20s finished TikTok; assemble multiple independently cleared clips if needed.
5. Run `python scripts/video_preflight.py <path-to-mp4>` using the script's supported CLI; verify FFmpeg/ffprobe results. This is technical QA only; audio quality, visuals, originality, Swiss advertising compliance and ≥85/100 editorial score need separate review.
6. Assign a unique immutable source/video hash and a publication idempotency key; block duplicate publication attempts.
7. Store provenance (source=Arena, generation timestamp, original prompt, source model if disclosed, source video path/hash, rights evidence, QA result, user approval timestamp, publication confirmation).
8. Metricool brand 7820933 / TikTok @dy3ko4nveu0o remains **NO PUBLISH** until the exact file passes technical, visual, audio, legal, advertising and explicit user-approval gates. Never activate old drafts.
9. Only after a verified public TikTok URL may the existing 24h analytics workflow consider the video.

## Integration decision
Arena is a **manual input provider**, not an automated provider. The generator router must never attempt Arena browser automation or assume an Arena video API endpoint, quota, zero price, commercial rights or MP4 URL. Prefer supported, licensed automated generators for unattended jobs. When unavailable, record a blocked job and request a one-time manual Arena download/import; do not mark the job complete.

No purchases, subscriptions, uploads, publishing, or third-party access have been authorized by this document.
