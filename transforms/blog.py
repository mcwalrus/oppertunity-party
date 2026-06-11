"""Transform blog posts from data/ to site/src/content/blog/."""

from pathlib import Path

from transforms.clean import (
    clean_body,
    extract_metadata_fields,
    normalise_blank_runs,
)


def transform_blog(data_dir: Path, content_dir: Path) -> None:
    """Read data/blog/ and write clean markdown to site/src/content/blog/."""
    blog_dir = data_dir / "blog"
    out_dir = content_dir / "blog"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not blog_dir.exists():
        return

    for md_file in sorted(blog_dir.glob("*.md")):
        if md_file.name == "index.json":
            continue

        body = md_file.read_text(encoding="utf-8")
        fields, body = extract_metadata_fields(body)

        title = fields.get("Title", md_file.stem)
        date = fields.get("Date", "")
        author = fields.get("Author", "")
        url = fields.get("URL", "")
        scraped = fields.get("Scraped", "")

        # Derive slug from filename (date prefix already there)
        slug = md_file.stem

        # Clean body — pass title to strip duplicate H1
        body = clean_body(body, title=title, strip_media_contact=False)

        # Build frontmatter
        frontmatter_lines = ["---", f'title: "{_esc(title)}"', f"slug: {slug}"]
        if date:
            frontmatter_lines.append(f'date: "{_esc(date)}"')
        if author:
            frontmatter_lines.append(f'author: "{_esc(author)}"')
        if url:
            frontmatter_lines.append(f'url: "{_esc(url)}"')
        if scraped:
            frontmatter_lines.append(f'scrapedAt: "{_esc(scraped)}"')
        frontmatter_lines.append("---")

        frontmatter = "\n".join(frontmatter_lines)
        output = frontmatter + "\n" + body
        output = normalise_blank_runs(output)

        out_file = out_dir / f"{slug}.md"
        out_file.write_text(output, encoding="utf-8")
        print(f"  📝 blog/{slug}.md")


def _esc(value: str) -> str:
    return value.replace('"', '\\"')
