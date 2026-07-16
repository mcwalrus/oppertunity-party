# Dependencies

Every tool the project depends on, grouped by what it's used for. For the
canonical version pins, see `pyproject.toml`, `scripts/Brewfile`, and
`site/package.json`.

## Local environment

| Tool | Purpose |
| --- | --- |
| [`direnv`](https://direnv.net) | Loads `.envrc` on `cd` — stable `DAGSTER_HOME` + venv `PATH` |
| [`fnm`](https://github.com/Schniz/fnm) | Node version manager (reads `.node-version`) |
| [`pnpm`](https://pnpm.io) | Node package manager (used by `site/`) |
| [`uv`](https://docs.astral.sh/uv) | Python toolchain + dependency manager (reads `.python-version`) |
| [`just`](https://github.com/casey/just) | Task runner — see `justfile` for recipes |
| [`lefthook`](https://lefthook.com) | Git hook manager (pre-commit: ruff, ty, markdown-link-check, astro check) |

## Pipeline orchestration

| Tool | Purpose |
| --- | --- |
| [`dagster`](https://dagster.io) | Asset-based pipeline orchestrator — gives every artefact lineage + observability |
| [`dagster-webserver`](https://dagster.io) | Dagster UI (the `just dev` surface) |
| [`dagster-dg-cli`](https://docs.dagster.io/api/clis/dg) | Project scaffolding + asset/job launch (`dg launch`) |

## Web scraping (ingestion layer)

| Tool | Purpose |
| --- | --- |
| [`httpx`](https://www.python-httpx.org) | HTTP client for scraping requests |
| [`beautifulsoup4`](https://www.crummy.com/software/BeautifulSoup/) | HTML parsing |
| [`lxml`](https://lxml.de) | Fast HTML/XML parser (BeautifulSoup backend) |
| [`markdownify`](https://github.com/matthewwithanm/python-markdownify) | HTML → Markdown for cleaned content |
| [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) | YouTube video + metadata + subtitle download |
| [`pymupdf4llm`](https://pymupdf.io) | PDF → Markdown for policy documents |
| [`gdown`](https://github.com/wkentaro/gdown) | Google Drive downloads |
| [`questionary`](https://github.com/twentyfortysix/questionary) | Interactive CLI prompts (e.g. `--clean`) |
| [`rich`](https://rich.readthedocs.io) | Terminal output formatting + progress |

## Site generation

| Tool | Purpose |
| --- | --- |
| [`astro`](https://astro.build) | Static-site generator for `site/` |
| [`@astrojs/check`](https://docs.astro.build/en/reference/cli-reference/#astro-check) | Astro template type-checking |
| [`typescript`](https://www.typescriptlang.org) | Site TS compiler |

## Python developer tooling

| Tool | Purpose |
| --- | --- |
| [`ruff`](https://docs.astral.sh/ruff) | Linter + formatter (replaces black, isort, flake8) |
| [`ty`](https://github.com/astral-sh/ty) | Static type checker (pre-commit strict) |

## MCP server (optional, not part of the README pipeline)

| Tool | Purpose |
| --- | --- |
| [`mcp`](https://modelcontextprotocol.io) | Model Context Protocol server runtime |

The MCP server reads from `data/clean/` for downstream tool integrations. It is
not part of the main scrape → clean → site pipeline and is excluded from the
README intentionally.