"""Media downloader package — enumerate, group, select, download."""

from __future__ import annotations

from media.platform import MediaPlatform
from media.youtube import YouTubePlatform

__all__ = ["MediaPlatform", "YouTubePlatform"]
