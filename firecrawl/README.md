# Firecrawl — Opportunity Party Site Mirror

This folder manages **Firecrawl** runs against <https://www.opportunity.org.nz/>.  
It is intentionally **separate from the Dagster pipeline** so crawling the live website is a deliberate, on-demand action — not something that happens every time you materialise assets.

---

## What is Firecrawl?

[Firecrawl](https://www.firecrawl.dev) is a web-crawling service that converts any website into clean, LLM-ready content.  
Key capabilities used here:

| Endpoint | Purpose |
|---|---|
| `map` | Discover every URL on the site |
| `download` | Save all pages as local markdown files |
| `crawl` | Bulk-extract into structured JSON |
| `scrape` | Extract a single page |

The CLI (`firecrawl-cli`) is installed locally via `pnpm` and is the primary tool.

---

## Why Separate from Dagster?

The main pipeline (`transforms/`) is Dagster-managed and runs from pre-downloaded sources stored under `data/sources/`.  
Firecrawl hits the **live website** each time — which is slow, costs API credits, and should not happen automatically on every `dagster materialize`.

Use this folder when you want to:

- **Re-scrape** the site to pick up new content
- **Compare** the live site against the Dagster-transformed data in `data/clean/`
- **Generate `llms.txt` / `llms-full.txt`** for LLM consumption
- **Spot-check** a specific page against the pipeline output

---

## Setup

The API key is stored in `.firecrawl-api-key` (gitignored) and loaded automatically by `direnv` via `.envrc`.

```bash
direnv allow          # load FIRECRAWL_API_KEY into the shell
pnpm install          # install firecrawl-cli (already in node_modules)
```

Verify everything is working:

```bash
firecrawl --version   # should print 1.x.x
```

> **Note:** The `firecrawl` binary is provided by the local `node_modules/.bin/` directory.  
> If it is not on your `$PATH`, prefix commands with `./node_modules/.bin/firecrawl` or use `pnpm exec firecrawl`.

---

## Common Commands

### Map — discover all URLs

```bash
firecrawl map https://www.opportunity.org.nz/
```

Use `--search <query>` to filter results:

```bash
firecrawl map https://www.opportunity.org.nz/ --search "policy"
```

### Download — save entire site as local markdown

```bash
pnpm run download
```

This runs the script at `scripts/download.sh`, which saves pages under `output/`.  
Run it manually for a quick one-liner:

```bash
# 'download' lives under the 'experimental' (x) subcommand in firecrawl-cli v1.x
firecrawl x download https://www.opportunity.org.nz/ \
  --only-main-content \
  --limit 200 \
  -y
```

Downloaded files land in `.firecrawl/` (the CLI's default output directory, gitignored).

### Generate llms.txt

```bash
pnpm run generate-llms
```

This concatenates the downloaded markdown files into:

| File | Contents |
|---|---|
| `output/llms.txt` | Site index — titles and URLs of all pages |
| `output/llms-full.txt` | Full markdown content of every page |

Both files are gitignored by default (they can be large). Commit them intentionally if you want a snapshot.

### Scrape a single page

```bash
firecrawl scrape https://www.opportunity.org.nz/policies/
```

---

## Output Structure

```
firecrawl/
├── .firecrawl/              # CLI default output — created by `firecrawl download` (gitignored)
│   └── opportunity.org.nz/
│       ├── index.md
│       ├── policies/
│       │   └── index.md
│       └── ...
├── output/                  # Generated artefacts (gitignored)
│   ├── llms.txt             # Site index for LLMs
│   └── llms-full.txt        # Full page content for LLMs
└── scripts/
    ├── download.sh          # Runs firecrawl download
    └── generate-llms.sh     # Builds llms.txt + llms-full.txt from .firecrawl/
```

---

## llms.txt / llms-full.txt Format

These follow the informal [llmstxt convention](https://llmstxt.org/) — a plain-text format that gives LLMs a compact representation of a website.

- **`llms.txt`** — one line per page: `# Title\nURL\n` blocks, formatted for quick orientation.
- **`llms-full.txt`** — the same list, but each entry is followed by the full markdown content of that page, separated by `---` dividers.

There is no strict schema. Formatting is a guide — agents will understand the content regardless.

---

## Comparing with the Dagster Pipeline

| Aspect | Firecrawl (this folder) | Dagster pipeline (`transforms/`) |
|---|---|---|
| Source | Live website (on-demand) | Cached raw scrapes in `data/sources/` |
| Trigger | Manual (`pnpm run download`) | `dagster materialize` |
| Output | `.firecrawl/` markdown, `output/llms*.txt` | `data/clean/` normalized markdown |
| Frequency | When you choose to re-crawl | On every pipeline run |

To diff the two outputs:

```bash
# Compare a specific page
diff \
  .firecrawl/opportunity.org.nz/policies/index.md \
  ../../data/clean/policies/index.md
```

---

## Gitignore

Sensitive and large generated files are excluded:

```
node_modules/       # pnpm install artifacts
.firecrawl/         # CLI download output
output/             # generated llms files
.env*               # environment files
.firecrawl-api-key  # API key (already in .gitignore)
```

Commit `llms.txt` / `llms-full.txt` intentionally if you want a versioned snapshot of the site.
