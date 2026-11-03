-- Run in Supabase SQL editor after project creation.
-- Keep bucket private by default; use time-limited signed URLs for external publishing.
create table if not exists public.dealradar_video_jobs (
 id text primary key,
 sha256 text not null unique,
 storage_path text,
 status text not null check (status in ('GENERATED','VALIDATED','UPLOADED','SUBMITTED','SCHEDULED','LIVE','FAILED','NEEDS_REVIEW')),
 external_post_id text unique,
 published_at timestamptz,
 last_error text,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
alter table public.dealradar_video_jobs enable row level security;
-- Do not create permissive public policies. Only server-side service-role access.
