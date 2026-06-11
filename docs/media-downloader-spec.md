# Media Downloader Spec

## Problem

The NZ Opportunity Party publishes content across multiple platforms — YouTube (videos + shorts), Substack (newsletter posts), Facebook (posts + videos), and Instagram (posts + reels) — but the existing website scraper only covers the main opportunity.org.nz site. There is no way to enumerate, browse, and selectively download that off-platform content. Baseline: all off-platform content is invisible to the scraper; any archival must be done manually, one piece at a time.

## Appetite

Small batch. YouTube is the only platform implemented this cycle. The architecture must accommodate Substack, Facebook, and Instagram as future platform slots, but no code is written for them now.

## Solution

A platform-aware media downloader built around a generic pipeline: **enumerate → group → select → download**. Each platform provides its own implementation of these four stages. The pipeline is driven from the CLI via `main.py`, consistent with the existing scraper sub-command pattern.

### Core abstraction: `MediaPlatform`

A protocol (or base class) that each platform implements:

- `enumerate()` — walk the source, collect metadata, cache results as JSON
- `group(items)` — organise items for browsing (YouTube: by year; others TBD)
- `select(grouped_items)` — interactive CLI selection (rich + questionary)
- `download(queue)` — fetch selected items to local storage, rate-limited

Only `YouTubePlatform` is implemented. Substack, Facebook, and Instagram are expressed as named slots in the platform registry — no stubs, no dead code, just the architectural contract that they would satisfy.

### YouTube details

Uses `yt-dlp` in flat-extraction mode to enumerate the @OpportunityNZ channel (videos tab + shorts tab). Metadata is cached in `data/youtube/channel_videos.json` so re-runs are fast. Interactive selection shows videos grouped by year; user marks items for download. Downloads go to `downloads/youtube/{year}/{title}-{id}.{ext}` with a 2-second sleep between each.

### Happy path (YouTube)

1. `python main.py media youtube --mode=list` — enumerates channel, shows year summary
2. `python main.py media youtube --mode=download` — interactive: pick year → mark videos → download
3. `python main.py media youtube --refresh` — force re-enumeration, replaces JSON cache
4. `python main.py media youtube --year=2024` — filter to a specific year

### Platform registry (future slots)

| Platform | Status | Notes |
|----------|--------|-------|
| YouTube | **Implemented** | `yt-dlp` flat extraction, videos + shorts |
| Substack | Architecture only | RSS feed for enumeration; download = HTML-to-markdown |
| Facebook | Architecture only | Auth required; `yt-dlp` or Graph API; anti-bot risk |
| Instagram | Architecture only | Auth required; `yt-dlp` for reels; rate-limiting strict |

## Rabbit Holes

- **Substack content fetching** — RSS gives metadata; full post content needs HTML scraping or newsletter API. Unresolved, descoped.
- **Facebook anti-bot measures** — Facebook aggressively blocks automated access. Likely needs authenticated sessions. Unresolved, descoped.
- **Instagram authentication** — Requires login credentials for most content. Unresolved, descoped.
- **Cross-platform metadata shape** — Each platform has different fields (YouTube has duration, Substack has author, Instagram has carousel). Use a per-platform model, not a single union type. The generic pipeline operates on `list[Any]`; each platform defines its own item dataclass.
- **yt-dlp as a multi-platform tool** — `yt-dlp` actually supports Facebook, Instagram, and Substack URLs, but with varying reliability and auth requirements. Only YouTube is in scope; the others' `yt-dlp` support is noted for future reference, not relied on.
- **Rate limiting specifics** — YouTube's limits are well-documented and permissive with `extract_flat`. A 2-second sleep between downloads is conservative enough. For future platforms, rate-limiting will need platform-specific tuning.

## No-Gos

- No implementation for Substack, Facebook, or Instagram — architecture only
- No stubs, scaffold, or placeholder code for unbuilt platforms
- No upload or publish capability — this is download-only
- No bulk downloading without user selection — interactive pick is mandatory
- No content that requires authentication (YouTube public channel only)
- No video processing, transcoding, or format conversion after download
- No scheduling, cron, or recurring download automation
- No UI beyond CLI (rich tables + interactive prompts)
- No changes to the existing website scraper modules

## Done When

- `python main.py media youtube --mode=list` enumerates all videos + shorts from @OpportunityNZ and displays a year-grouped summary
- `python main.py media youtube --mode=download` presents an interactive selector; user can pick specific videos and they download successfully
- `python main.py media youtube --refresh` forces re-enumeration and updates the JSON cache
- `python main.py media youtube --year=2024` filters to that year only
- Metadata is cached in `data/youtube/channel_videos.json`; re-runs without `--refresh` use the cache
- Downloads land in `downloads/youtube/{year}/{title}-{id}.{ext}`
- The downloader uses a `MediaPlatform` abstraction that can accommodate future platforms without restructuring
- `just check` passes (ruff + ty)
- The old `docs/youtube-downloader-impl-plan.md` is removed (this spec replaces it)