"""Validate docs/**/*.md external links via hyperlink + curl.

hyperlink (https://github.com/untitaker/hyperlink) is a fast static-site link
checker. It doesn't validate external URLs on its own, but its
``dump-external-links`` subcommand extracts every absolute URL from a folder
of HTML — we then HEAD-check each one with curl.

Workflow:
  1. Render docs/*.md to a tmp HTML dir using python-markdown
  2. Strip root-relative hrefs (``<a href="/foo">``) — those are legitimate
     NationBuilder navigation paths already ignored by markdown-link-check
     via ``.markdown-link-check.json``
  3. ``hyperlink dump-external-links --base-path=<tmp>`` → list of URLs
  4. ``curl -sILf`` each URL; non-2xx/3xx is a failure

hyperlink's internal-link check is deliberately skipped: docs reference files
across the repo (``../../AGENTS.md``, ``../data/clean/...``) which hyperlink
re-anchors at its root and flags as broken. Cross-tree validation belongs to
markdown-link-check (already wired up for ``data/clean/**/*.md``).
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import markdown

DOCS = Path("docs")
CURL_UA = "Mozilla/5.0 (compatible; docs-link-check/1)"

# ponytail: npx --yes fetches the binary on first run; cache hits after that.
# If a maintainer wants to skip the download, install once with
# `npm install -g @untitaker/hyperlink` and the local-binary branch kicks in.
NPX_FALLBACK = ["npx", "--yes", "@untitaker/hyperlink"]
ROOT_REL_HREF_RE = re.compile(r'<a href="(/[^"]*)"')


def hyperlink_cmd(*args: str) -> list[str]:
    """Build the hyperlink invocation; prefer a globally installed binary."""
    binary = shutil.which("hyperlink")
    if binary is not None:
        return [binary, *args]
    return [*NPX_FALLBACK, *args]


def render_docs(tmp_docs: Path) -> None:
    """Render every docs/*.md to <tmp_docs>/<rel>.html with root-rel hrefs stripped."""
    md = markdown.Markdown(extensions=["extra", "sane_lists", "toc"])
    for md_file in sorted(DOCS.rglob("*.md")):
        rel = md_file.relative_to(DOCS)
        html_path = (tmp_docs / rel).with_suffix(".html")
        html_path.parent.mkdir(parents=True, exist_ok=True)
        body = md.convert(md_file.read_text(encoding="utf-8"))
        md.reset()
        html_path.write_text(ROOT_REL_HREF_RE.sub("<a", body), encoding="utf-8")


def extract_external_urls(tmp_docs: Path) -> list[str]:
    """Return the absolute URLs hyperlink finds in <tmp_docs>."""
    dump = subprocess.run(
        hyperlink_cmd("dump-external-links", f"--base-path={tmp_docs}"),
        capture_output=True,
        text=True,
        check=False,
    )
    return [u for u in dump.stdout.splitlines() if u.startswith(("http://", "https://"))]


def head_check(urls: list[str]) -> list[str]:
    """HEAD-check each URL; return URLs whose final status is not in ALIVE_STATUS.

    Accepts the same status set as .markdown-link-check.json (200/206/403/999)
    and retries on 429 — bots are routinely throttled but the page still loads
    for real users.
    """
    failures: list[str] = []
    for url in urls:
        for attempt in range(3):
            result = subprocess.run(
                [
                    "curl",
                    "-sIL",
                    "-o",
                    "/dev/null",
                    "--max-time",
                    "15",
                    "-A",
                    CURL_UA,
                    "-w",
                    "%{http_code}",
                    url,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            status = result.stdout.strip().splitlines()[-1] if result.stdout else ""
            # 429 = throttled; back off and retry. curl exits non-zero on hard
            # failures, so we also bail on rc != 0 after the retry budget.
            if status == "429" and attempt < 2:
                time.sleep(2 + attempt * 3)
                continue
            if status in {"200", "206", "403", "999"}:
                break
            failures.append(url)
            break
        else:
            failures.append(url)
    return failures


def main() -> int:
    if not DOCS.exists():
        print("docs/ not found; nothing to validate.", file=sys.stderr)
        return 0

    with tempfile.TemporaryDirectory() as tmp:
        tmp_docs = Path(tmp) / "docs"
        render_docs(tmp_docs)
        urls = extract_external_urls(tmp_docs)
        failures = head_check(urls)
        if failures:
            print(
                f"External link failures ({len(failures)}/{len(urls)} HEAD non-2xx):",
                file=sys.stderr,
            )
            for u in failures:
                print(f"  {u}", file=sys.stderr)
            return 1
        print(f"docs link check: {len(urls)} external URLs OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
