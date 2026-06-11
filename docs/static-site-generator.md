
Develop a specification to present a static-site-generator for the collected information under ./data as plain text. The framework I want to use is astro. Consider how I can restructure the application.

https://astro.build/

Ideally, I want to manage a tiered approach to manage information which is scraped by python vs what is used to present from the static-site-generator. This is to reflect the content found on the Opportunity Party's website, but in a way which is LLM approachable.


**For example:** 

Anthropic provides this for their product with a single index file for their platform:

**[https://docs.claude.com/en/docs_site_map.md](https://docs.claude.com/en/docs_site_map.md)**

They also provide an index map per product as well:

**[https://docs.anthropic.com/en/docs/claude-code/claude_code_docs_map.md](https://docs.anthropic.com/en/docs/claude-code/claude_code_docs_map.md)**

This links to plain-text documentation pages of their products:

**https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview.md** 


**Requirements:**

- [ ] Structure presented data slightly differently to how it is represented in data.
- [ ] Develop a static-site-generator to display the md document information.
- [ ] Have the static-site regenerate daily for updates regarding news and events.
- [ ] Use scripts to perform translations from ./data to however the static site will be represented.
- [ ] Consider deployment engines, i.e sites which I can use to present the website.


**Additional Considerations:**

- [ ] Pre-commit CI, typescript if any code is needed.
- [ ] Local scoping of astro as a package for environment management.

	---

## Shaped Spec

### Problem

The scraped Opportunity Party content in `./data` is only accessible as a local Obsidian vault. There's no public-facing website and no LLM-accessible plain-text layer. The scraped markdown files are noisy — they mix scraper metadata headers, external CDN image tags, and navigation cruft into the content. Baseline: raw flat markdown on disk, viewable in Obsidian only.

### Appetite

**Full cycle.** Five scopes with clear dependencies, roughly a week of agent work. The value is two things: a deployable website reflecting the party's content, and an Anthropic-style plain-text LLM layer (`/policies.md`, `/docs_site_map.md`, per-item `.md` endpoints) making the content AI-accessible.

### Solution

**Three-tier architecture:**

| Tier | What it is | Managed by |
|------|-----------|------------|
| 1 — Raw data | `./data/` scraped markdown + JSON | Existing Python scraper (unchanged) |
| 2 — Site content | `./site/src/content/` clean frontmatter markdown | New Python transform scripts |
| 3 — Site | `./site/` Astro project | New Astro app |

**Scope A — Transform scripts** (`transforms/` module)

Python scripts run via `just transform` that read each content type from `data/` and write cleaned Astro-compatible markdown to `site/src/content/`. One transform function per content type: `policies`, `blog`, `events`, `team`, `party-info`.

Each transform:
- Promotes structured fields (title, date, URL, author, etc.) to YAML frontmatter
- Strips the leading `> **URL**: ...` / `> **Scraped**: ...` blockquote
- Strips `![...](...)` image tags
- Strips everything from `### Check out more policies` or `## Get Involved` to end-of-file
- Appends PDF content (from `pdf-*.md` siblings in the policy directory) as a `## Full Policy Detail` section at the end of each policy file

Happy path (policy):
1. Read `data/policies/tax-reset/tax-reset.md` + `pdf-policy-overview.md` + `pdf-policy-addendum.md`
2. Extract frontmatter fields from metadata lines
3. Strip noise
4. Write `site/src/content/policies/tax-reset.md` with clean YAML frontmatter + body + PDF content section

**Scope B — Astro project scaffold** (`site/`)

New Astro project (`pnpm create astro`) in `site/`. Content collections defined for `policies`, `blog`, `events`, `team`, `party-info`, each with a Zod schema matching the frontmatter fields produced by the transform. `astro.config.mjs` set to `output: 'static'`.

**Scope C — HTML pages**

Astro pages for:
- `/` — home: party summary + links to all sections
- `/policies` — grid/list of all policies
- `/policies/[slug]` — individual policy page with full content
- `/blog` — blog post list sorted by date descending
- `/blog/[slug]` — individual post
- `/events` — upcoming events list sorted by date
- `/team` — team member grid
- `/team/[slug]` — individual team member profile
- `/about` — party information

No styling framework required. Basic readable HTML is fine. No design system this cycle.

**Scope D — LLM plain-text layer**

Astro endpoint routes (`.ts` files returning `text/plain`) at:
- `GET /docs_site_map.md` — root index with title, one-line description, and links to all section maps
- `GET /policies.md` — all policies, each as a heading + one-paragraph summary
- `GET /blog.md` — all posts as `## [date] [title]` with first 100 words
- `GET /events.md` — upcoming events with date, location, title
- `GET /team.md` — all team members with role and electorate
- `GET /policies/[slug].md` — full plain-text policy content
- `GET /blog/[slug].md` — full plain-text blog post

Structure follows Anthropic's pattern: root sitemap → section maps → individual item pages.

**Scope E — Deployment + CI**
- `justfile` gets `transform` and `site-build` recipes added
- GitHub Actions workflow at `.github/workflows/daily-publish.yml`: runs on `schedule: cron: '0 2 * * *'`, runs `just scrape && just transform && just site-build`, deploys the `site/dist/` output

### Rabbit Holes

**PDF content per policy** — Some policies have zero, one, or multiple `pdf-*.md` files. The transform should iterate all `pdf-*.md` siblings in alpha order and concatenate them under `## Full Policy Detail`. If none exist, that section is omitted. No branching logic needed per policy.

**Policy content source** — Each policy slug directory always has a `[slug].md` (scraped page). Use that as the primary source. The `data/policies/index.json` content field is redundant — ignore it in the transform.

**Noise patterns to strip** — The scraper inserts consistent patterns. The transform can strip by matching:
- Lines matching `^> \*\*(URL|Scraped)\*\*:` — drop these
- Lines matching `^\*\*(Title|Date|Author|Location|URL|Scraped|When|Venue|Address|Role|Electorate)\*\*:` — move to frontmatter, don't leave in body
- Image lines matching `^!\[` — drop entirely
- Everything from `### Check out more policies` or `## Get Involved` to EOF — drop
- Trailing whitespace / blank line runs — normalise to single blank lines

**Astro text endpoints** — Astro static mode supports endpoint routes returning custom content types via `export async function GET()`. Use `getCollection()` inside these endpoints. The agent determines exact implementation — no decision needed from shaper.

**Daily scrape and stale events** — The scraper may return past events. The transform passes them through; the site's events page can filter to `date >= today` at build time. This is a build-time filter, not a runtime one — static is fine.

**`just transform` idempotency** — The transform should wipe and rewrite `site/src/content/` on each run to avoid stale files from deleted scraper output. Use `shutil.rmtree` + recreate on each invocation.

### No-Gos

- No changes to the Python scraper or `data/` structure
- No search functionality
- No interactive components (comments, contact forms, sign-up flows)
- No server-side rendering — static output only
- No CSS framework or design system (basic HTML layout, agent can add minimal inline styles or a single CSS file)
- No image hosting or proxy — images are stripped from all output
- No PDF serving from the site — PDF content is embedded via the transform
- No i18n or te reo Māori translation layer
- No MCP server changes this cycle

### Done When

- `just transform` completes without error and `site/src/content/` contains all content types with clean frontmatter markdown
- `just site-build` (`astro build`) completes with zero errors; output in `site/dist/`
- `GET /docs_site_map.md` returns a valid plain-text root index linking to all section maps
- `GET /policies/tax-reset.md` returns clean plain-text policy content (no `> **URL**:` lines, no image tags, no "Get Involved" footer)
- `GET /policies/[slug]` HTML page renders the full policy including PDF detail section for policies that have PDFs
- GitHub Actions workflow file exists at `.github/workflows/daily-publish.yml` and is syntactically valid YAML with a daily cron trigger
- Deployment configuration file (`wrangler.toml` or equivalent) is present in `site/` with the project name set

## Other

We will use CloudFlare as the site host.

I have created a reference for astro under ./docs/reference/astro

If you are unsure for CloudFlare setup, feel free to ignore this for now