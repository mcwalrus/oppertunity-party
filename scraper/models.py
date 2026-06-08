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
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TeamMember:
    """A team member / candidate entry."""

    name: str
    role: str = ""
    url: str = ""
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
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())