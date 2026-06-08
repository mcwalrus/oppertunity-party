"""Data models for scraped content."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PolicyPage:
    """A single policy page from the website."""

    slug: str
    title: str
    url: str
    content: str = ""
    pdf_downloads: list[str] = field(default_factory=list)
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TeamMember:
    """A team member / candidate entry."""

    name: str
    role: str = ""  # e.g. "Party Leader", "Deputy Leader", "Candidate"
    url: str = ""
    slug: str = ""  # derived from URL path, e.g. "daniel-eb" from /candidate-daniel-eb
    electorate: str = ""  # NZ electorate the candidate is contesting, e.g. "Mt. Albert"
    content: str = ""
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class NewsItem:
    """A news / media release entry."""

    title: str
    url: str = ""
    date: str = ""
    excerpt: str = ""
    content: str = ""
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PartyInfo:
    """Party information page content."""

    section: str
    url: str
    content: str = ""
    pdf_downloads: list[tuple[str, str]] = field(default_factory=list)  # [(label, url), ...]
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())
