"""YouTubePlatform — enumerate/group/select/download for the @OpportunityNZ channel."""

from __future__ import annotations

import json
import logging
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import questionary
from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CHANNEL_URL = "https://www.youtube.com/@OpportunityNZ"
CACHE_PATH = Path("data/youtube/channel_videos.json")
DOWNLOAD_ROOT = Path("downloads/youtube")
DOWNLOAD_SLEEP = 2.0  # seconds between yt-dlp invocations


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class YouTubeVideo:
    """Metadata for a single YouTube video or short."""

    id: str
    title: str
    url: str
    upload_date: str  # YYYYMMDD string from yt-dlp
    duration: int | None = None  # seconds
    view_count: int | None = None
    tab: str = "videos"  # "videos" or "shorts"
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def year(self) -> str:
        """4-digit year string extracted from upload_date."""
        return self.upload_date[:4] if len(self.upload_date) >= 4 else "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "upload_date": self.upload_date,
            "duration": self.duration,
            "view_count": self.view_count,
            "tab": self.tab,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> YouTubeVideo:
        return cls(
            id=data["id"],
            title=data["title"],
            url=data["url"],
            upload_date=data.get("upload_date", ""),
            duration=data.get("duration"),
            view_count=data.get("view_count"),
            tab=data.get("tab", "videos"),
        )


# ---------------------------------------------------------------------------
# Platform implementation
# ---------------------------------------------------------------------------


class YouTubePlatform:
    """MediaPlatform implementation for the @OpportunityNZ YouTube channel.

    Enumerate
    ---------
    Uses ``yt-dlp`` in flat-extraction mode (``--flat-playlist``) to collect
    metadata from both the /videos and /shorts tabs.  Results are cached at
    ``data/youtube/channel_videos.json``; subsequent runs read from the cache
    unless ``--refresh`` is passed.

    Group
    -----
    Items are grouped by upload year, newest year first.

    Select
    ------
    Presents a ``rich`` year-summary table, then uses ``questionary`` checkboxes
    to let the user mark individual videos for download.

    Download
    --------
    Calls ``yt-dlp`` for each chosen video, writing files to
    ``downloads/youtube/{year}/{title}-{id}.{ext}``.  A 2-second sleep is
    inserted between downloads.
    """

    def __init__(self, year_filter: str | None = None) -> None:
        self._year_filter = year_filter
        self._console = Console()

    # ------------------------------------------------------------------
    # enumerate
    # ------------------------------------------------------------------

    def enumerate(self, *, refresh: bool = False) -> list[YouTubeVideo]:
        """Walk the channel, collect metadata, cache to JSON.

        Parameters
        ----------
        refresh:
            When *True*, bypass the cache and re-fetch from YouTube.

        Returns
        -------
        list[YouTubeVideo]
            All videos + shorts found on the channel.
        """
        if not refresh and CACHE_PATH.exists():
            logger.info("Loading YouTube metadata from cache: %s", CACHE_PATH)
            return self._load_cache()

        logger.info("Enumerating @OpportunityNZ channel (this may take a minute)…")
        videos: list[YouTubeVideo] = []

        for tab in ("videos", "shorts"):
            tab_url = f"{CHANNEL_URL}/{tab}"
            logger.info("  Fetching tab: %s", tab_url)
            raw = self._yt_dlp_flat(tab_url)
            for entry in raw:
                vid = self._parse_entry(entry, tab=tab)
                if vid is not None:
                    videos.append(vid)
            logger.info("  Found %d item(s) in %s tab", len(raw), tab)

        # Deduplicate by id (a short might also appear in videos tab)
        seen: set[str] = set()
        unique: list[YouTubeVideo] = []
        for v in videos:
            if v.id not in seen:
                seen.add(v.id)
                unique.append(v)

        self._save_cache(unique)
        logger.info("Cached %d videos to %s", len(unique), CACHE_PATH)
        return unique

    @staticmethod
    def _python_exe() -> str:
        """Return a Python executable that can open network sockets.

        CPython 3.12 on macOS 26 has a bug (errno 9 / EBADF) that prevents
        socket.connect() from working inside a uv venv subprocess.  The system
        Python 3.13 at /usr/local/bin/python3 is unaffected, so we probe for
        it explicitly before falling back to the current interpreter.
        """
        import sys

        venv_prefix = sys.prefix  # e.g. /project/.venv

        # Common system Python locations on macOS / Linux, newest first
        candidates = [
            "/usr/local/bin/python3",
            "/usr/bin/python3",
            "/opt/homebrew/bin/python3",
        ]
        for path in candidates:
            from pathlib import Path as _Path

            p = _Path(path)
            if p.exists() and not str(p.resolve()).startswith(venv_prefix):
                return str(p)

        return sys.executable

    def _yt_dlp_flat(self, url: str) -> list[dict[str, Any]]:
        """Run yt-dlp --flat-playlist and return the parsed entries."""
        python = self._python_exe()
        cmd = [
            python,
            "-m",
            "yt_dlp",
            "--flat-playlist",
            "--dump-json",
            "--no-warnings",
            "--ignore-errors",
            url,
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except FileNotFoundError:
            logger.error("yt-dlp not found — install it with: uv add yt-dlp")
            return []
        except subprocess.TimeoutExpired:
            logger.error("yt-dlp timed out enumerating %s", url)
            return []

        entries: list[dict[str, Any]] = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                logger.debug("Skipping non-JSON line: %s", line[:80])
        return entries

    def _parse_entry(self, entry: dict[str, Any], tab: str) -> YouTubeVideo | None:
        vid_id = entry.get("id") or entry.get("url", "")
        if not vid_id:
            return None
        title = entry.get("title") or entry.get("ie_key", vid_id)
        url = entry.get("url") or f"https://www.youtube.com/watch?v={vid_id}"
        if not url.startswith("http"):
            url = f"https://www.youtube.com/watch?v={vid_id}"
        upload_date = entry.get("upload_date") or ""
        return YouTubeVideo(
            id=vid_id,
            title=title,
            url=url,
            upload_date=upload_date,
            duration=entry.get("duration"),
            view_count=entry.get("view_count"),
            tab=tab,
        )

    def _load_cache(self) -> list[YouTubeVideo]:
        with CACHE_PATH.open(encoding="utf-8") as f:
            data = json.load(f)
        return [YouTubeVideo.from_dict(d) for d in data]

    def _save_cache(self, videos: list[YouTubeVideo]) -> None:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CACHE_PATH.open("w", encoding="utf-8") as f:
            json.dump([v.to_dict() for v in videos], f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # group
    # ------------------------------------------------------------------

    def group(self, items: list[Any]) -> dict[str, list[Any]]:
        """Group videos by upload year, newest year first.

        Parameters
        ----------
        items:
            List of :class:`YouTubeVideo` objects.

        Returns
        -------
        dict[str, list[Any]]
            Year strings mapped to lists of videos.
        """
        videos = [v for v in items if isinstance(v, YouTubeVideo)]

        # Apply year filter if set
        if self._year_filter:
            videos = [v for v in videos if v.year == self._year_filter]

        grouped: dict[str, list[YouTubeVideo]] = {}
        for v in videos:
            grouped.setdefault(v.year, []).append(v)

        # Sort: newest year first
        return dict(sorted(grouped.items(), reverse=True))

    # ------------------------------------------------------------------
    # list (non-interactive summary)
    # ------------------------------------------------------------------

    def list_summary(self, grouped: dict[str, list[Any]]) -> None:
        """Print a rich year-grouped summary table to stdout."""
        table = Table(title="@OpportunityNZ — YouTube Videos", show_lines=False)
        table.add_column("Year", style="bold cyan", justify="right")
        table.add_column("Count", justify="right")
        table.add_column("Tabs", style="dim")

        total = 0
        for year, vids in grouped.items():
            tabs = sorted({v.tab for v in vids if isinstance(v, YouTubeVideo)})
            table.add_row(year, str(len(vids)), ", ".join(tabs))
            total += len(vids)

        self._console.print(table)
        self._console.print(f"[bold]Total:[/bold] {total} videos")

    # ------------------------------------------------------------------
    # select
    # ------------------------------------------------------------------

    def select(self, grouped_items: dict[str, list[Any]]) -> list[Any]:
        """Interactive year → video selection via questionary checkboxes.

        Parameters
        ----------
        grouped_items:
            Mapping of year → list of :class:`YouTubeVideo`.

        Returns
        -------
        list[Any]
            User-selected :class:`YouTubeVideo` objects.
        """
        years = list(grouped_items.keys())
        if not years:
            self._console.print("[yellow]No videos found.[/yellow]")
            return []

        # Step 1: pick years
        year_choices = [
            questionary.Choice(
                title=f"{y}  ({len(grouped_items[y])} videos)",
                value=y,
            )
            for y in years
        ]
        chosen_years: list[str] | None = questionary.checkbox(
            "Select year(s) to browse:",
            choices=year_choices,
        ).ask()

        if not chosen_years:
            self._console.print("[yellow]No years selected.[/yellow]")
            return []

        # Step 2: for each chosen year, pick individual videos
        selected: list[Any] = []
        for year in chosen_years:
            vids = grouped_items[year]
            video_choices = [
                questionary.Choice(
                    title=self._video_label(v),
                    value=v,
                )
                for v in vids
                if isinstance(v, YouTubeVideo)
            ]
            if not video_choices:
                continue

            chosen_vids: list[Any] | None = questionary.checkbox(
                f"Select videos from {year}:",
                choices=video_choices,
            ).ask()

            if chosen_vids:
                selected.extend(chosen_vids)

        return selected

    def _video_label(self, v: YouTubeVideo) -> str:
        """Human-readable label for a video in the checkbox list."""
        dur = ""
        if v.duration:
            m, s = divmod(v.duration, 60)
            dur = f"  [{m}:{s:02d}]"
        tab_tag = " [short]" if v.tab == "shorts" else ""
        return f"{v.title}{dur}{tab_tag}"

    # ------------------------------------------------------------------
    # download
    # ------------------------------------------------------------------

    def download(self, queue: list[Any]) -> None:
        """Download selected videos via yt-dlp.

        Parameters
        ----------
        queue:
            List of :class:`YouTubeVideo` objects to download.
        """
        if not queue:
            self._console.print("[yellow]Nothing to download.[/yellow]")
            return

        self._console.print(f"[bold green]Downloading {len(queue)} video(s)…[/bold green]")

        for i, item in enumerate(queue, start=1):
            if not isinstance(item, YouTubeVideo):
                continue

            dest_dir = DOWNLOAD_ROOT / item.year
            dest_dir.mkdir(parents=True, exist_ok=True)

            # yt-dlp output template: {title}-{id}.{ext}
            safe_title = _slugify(item.title)
            output_template = str(dest_dir / f"{safe_title}-{item.id}.%(ext)s")

            self._console.print(f"  [{i}/{len(queue)}] [cyan]{item.title}[/cyan]")
            python = self._python_exe()
            cmd = [
                python,
                "-m",
                "yt_dlp",
                "--no-warnings",
                "--ignore-errors",
                "-o",
                output_template,
                item.url,
            ]
            try:
                result = subprocess.run(cmd, capture_output=False, timeout=600)
                if result.returncode != 0:
                    logger.warning("yt-dlp exited %d for %s", result.returncode, item.url)
            except FileNotFoundError:
                logger.error("yt-dlp not found")
                return
            except subprocess.TimeoutExpired:
                logger.error("yt-dlp timed out for %s", item.url)

            if i < len(queue):
                time.sleep(DOWNLOAD_SLEEP)

        self._console.print("[bold green]Done.[/bold green]")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slugify(text: str) -> str:
    """Convert a title to a safe filename component."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")[:80]
