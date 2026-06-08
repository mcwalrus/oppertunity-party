# Implementation Plan: Interactive YouTube Video Downloader

## Overview

A Python-based, interactive tool that uses `yt-dlp` to enumerate and selectively download videos from the [OpportunityNZ YouTube channel](https://www.youtube.com/@OpportunityNZ). The tool lists all videos and shorts, groups them by year, and allows the user to pick which ones to download interactively, avoiding bulk/spam downloading.

## Goals

| # | Goal |
|---|------|
| 1 | Enumerate **videos + shorts** from the channel without downloading anything yet |
| 2 | Sort and group content **by year** for easy navigation |
| 3 | Present an **interactive picker** (CLI) so the user can select individual videos or bulk-select by year |
| 4 | Download only the selected videos, with configurable quality/format options |
| 5 | Store metadata (title, URL, upload date, duration, etc.) so re-runs don't re-enumerate the full channel |
| 6 | Rate-limit / sleep between API calls to avoid hammering YouTube |

## Architecture

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   Enumerator    │─────▶│   Year Grouper   │─────▶│  Interactive    │
│   (yt-dlp)      │      │   (Python logic) │      │  Selector (CLI) │
└─────────────────┘      └──────────────────┘      └─────────────────┘
         │                                                  │
         │              ┌──────────────────┐                 │
         └─────────────▶│  Metadata Store  │◀────────────────┘
                        │  (JSON cache)    │
                        └──────────────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │   Downloader     │
                        │   (yt-dlp)       │
                        └──────────────────┘
```

## Components

### 1. `scraper/youtube.py` — The Core Module

A new module under `scraper/` containing:

#### `YouTubeChannel`
Dataclass representing a channel entry:
```python
@dataclass
class YouTubeVideo:
    id: str
    title: str
    url: str
    duration: int | None
    upload_date: str  # YYYYMMDD
    uploader: str
    view_count: int | None
    is_short: bool
    thumbnail: str | None
```

#### `YouTubeEnumerator`
- Uses `yt-dlp.YoutubeDL(extract_flat=True, playlistend=None)` to walk channel tabs:
  - `videos` tab
  - `shorts` tab
- Collects metadata for every entry
- Writes results to `data/youtube/channel_videos.json`
- Supports `--refresh` flag to force re-enumeration

#### `YearGrouper`
- Reads `channel_videos.json`
- Groups `YouTubeVideo` objects by `upload_date[:4]`
- Provides iterators: `by_year(year)`, `years()`, `all()`

#### `InteractiveSelector`
CLI interaction using `rich` + `questionary` (or built-in `input()`):
- Shows a table: `Year | Count | Total Duration`
- User picks a year → shows paginated list of videos
- User can:
  - `y` — download this video
  - `n` — skip
  - `a` — download all in this year
  - `q` — quit
- Maintains a `download_queue: list[YouTubeVideo]`

#### `YouTubeDownloader`
- Accepts a `download_queue`
- Iterates with a `time.sleep(2)` between downloads
- Configurable via `ytdl_opts` (format, output dir, etc.)
- Downloads to `downloads/youtube/{year}/{title}-{id}.{ext}`
- Logs progress

### 2. CLI Integration in `main.py`

Add a new sub-command:
```bash
python main.py youtube --mode=list          # Just list videos by year
python main.py youtube --mode=download     # Interactive download mode
python main.py youtube --refresh             # Force re-enumeration
python main.py youtube --year=2024           # Filter to a specific year
```

### 3. Dependencies

Add to `pyproject.toml`:
```toml
dependencies = [
    "yt-dlp",
    "rich>=13.0",       # Pretty tables & progress
    "questionary>=2.0", # Interactive prompts (optional, can use input())
]
```

## Data Flow

1. **Enumeration Phase**
   ```
   main.py youtube --mode=list
   │
   ▼
   YouTubeEnumerator.run()
   │  → yt-dlp extracts flat playlist from @OpportunityNZ/videos
   │  → yt-dlp extracts flat playlist from @OpportunityNZ/shorts
   │  → Build list[YouTubeVideo]
   ▼
   Save to data/youtube/channel_videos.json
   ```

2. **Interactive Phase**
   ```
   main.py youtube --mode=download
   │
   ▼
   YearGrouper.load() from JSON cache
   │
   ▼
   Display year menu (rich table)
   │  → User picks year → video list shown
   │  → User marks y/n/a for each
   ▼
   Build download_queue
   │
   ▼
   YouTubeDownloader.run(download_queue)
   │  → Sleep 2s between each
   │  → Save to downloads/youtube/
   ▼
   Done
   ```

## File Structure

```
scraper/
  youtube.py          # NEW: YouTubeEnumerator, YearGrouper, Selector, Downloader
  models.py           # UPDATE: add YouTubeVideo dataclass
data/
  youtube/
    channel_videos.json    # NEW: enumerated metadata cache
downloads/
  youtube/
    2024/
      video-title-abc123.mp4
    2023/
      ...
```

## Configuration

`data/youtube/config.json` (optional overrides):
```json
{
  "channel_url": "https://www.youtube.com/@OpportunityNZ",
  "output_dir": "downloads/youtube",
  "sleep_seconds": 2,
  "ytdl_format": "best[height<=1080]",
  "cache_file": "data/youtube/channel_videos.json"
}
```

## Error Handling

| Scenario | Strategy |
|----------|----------|
| Network timeout during enum | Retry with exponential backoff (3 attempts) |
| Private / deleted video | Log warning, skip entry |
| yt-dlp not installed | Exit with clear message: `pip install yt-dlp` |
| User Ctrl-C during select | Gracefully save partial queue, exit |
| Download fails mid-way | Log failed ID, continue with next, write `failed.json` |

## Testing Strategy

1. **Unit tests** (`tests/test_youtube.py`):
   - Mock `yt-dlp` responses with sample JSON
   - Test `YearGrouper` grouping logic
   - Test `InteractiveSelector` queue building

2. **Integration test** (manual):
   - Run `python main.py youtube --mode=list` on real channel
   - Verify JSON cache created correctly
   - Verify `--year=2024` filter works

3. **Rate-limit check**:
   - Confirm `sleep(2)` between downloads
   - Confirm enumeration uses `extract_flat` (lightweight, one API call per tab)

## Implementation Order

| Step | Task | File(s) |
|------|------|---------|
| 1 | Add `YouTubeVideo` model to `models.py` | `scraper/models.py` |
| 2 | Write `YouTubeEnumerator` with JSON cache | `scraper/youtube.py` |
| 3 | Write `YearGrouper` utility | `scraper/youtube.py` |
| 4 | Write `InteractiveSelector` CLI | `scraper/youtube.py` |
| 5 | Write `YouTubeDownloader` with sleep | `scraper/youtube.py` |
| 6 | Wire into `main.py` argument parser | `main.py` |
| 7 |