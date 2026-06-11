"""Transform scraped data from data/ into clean Astro-compatible markdown in site/src/content/."""

from transforms.main import transform_all

__all__ = ["transform_all"]
