# Dagster UI Screenshot Index

This index captures how Dagster is used in this project, organised by UI screen.
Each screenshot was captured from `localhost:3000` (the local Dagster UI) and
renamed to a stable, descriptive filename. Screenshots are ordered roughly in
the order they were taken.

> **Progress:** 10 / 10 screenshots documented. Built up incrementally to
> avoid hammering the image-read endpoint.

## How Dagster is used in this project

Dagster orchestrates the project's ETL pipeline. The code location lives at
`pipeline/`, with assets organised into three groups by their `group_name`:

- **`ingestion`** — scraping sources (policies, blog posts, news, team,
  events, governance)
- **`clean`** — normalising scraped output into `data/clean/`
- **`site`** — building the static site and resolving sitemaps

A fourth asset group — **`validation`** — was added to house PDF-pipeline
checks (see [`docs/pdf-pipeline.md`](../pdf-pipeline.md) for the design).

Jobs in [`pipeline/defs/jobs.py`](../../pipeline/defs/jobs.py) wire those
assets together:

- `full_pipeline` — everything except the production deploy
- `site_deploy_job` — Cloudflare Workers deploy (production-affecting,
  separate job)
- `ingestion_job`, `transforms_job`, `pdf_job` — narrower targeted runs

The screenshots below walk through the UI surfaces used to operate this
pipeline: lineage, runs, jobs, schedules, sensors, and asset detail.

---

## Screenshots

### 1. Lineage — `validation` group

**File:** `01-lineage-validation-group.png`

The **Global asset lineage** view, with the `validation` group expanded
(URL: `/asset-groups/?expanded=global%40global%3Avalidation`). Two assets
are visible in the group:

- `validate_pdf_extraction` — Materialized 16 Jul, 16:23 (37 min before the
  screenshot). Has an Automation schedule attached.
- `write_pdf_pipeline_report` — Materialized 16 Jul, 16:23. Also has an
  Automation schedule.

This view is the standard way to inspect the DAG shape of the validation
subset of the pipeline — useful for confirming the PDF-pipeline assets are
correctly grouped and that their dependencies resolve.

### 2. Lineage — collapsed group overview

**File:** `02-lineage-groups-overview.png`

The same **Global asset lineage** view, but with every group collapsed so
the high-level data flow is visible at a glance:

```
ingestion ─┬─► clean ─► site
           └─► validation
```

Asset counts and materialisation status per group:

| Group        | Healthy | Warning | Failed | Notes                              |
|--------------|---------|---------|--------|------------------------------------|
| `ingestion`  | 6       | 0       | 0      | All sources currently green        |
| `clean`      | 7       | 1       | 0      | One stale transform — yellow chip  |
| `site`       | 5       | 0       | 3      | Three site assets failing (red)    |
| `validation` | 2       | 0       | 0      | PDF pipeline assets (see entry 1)  |

The three red chips in `site` are the failing assets that motivated adding
the `validation` group — see [`docs/pdf-pipeline.md`](../pdf-pipeline.md)
for the failure mode and the assets introduced to detect it. This view
gives a one-glance health snapshot of the whole pipeline.

### 3. Lineage — `ingestion` group expanded

**File:** `03-lineage-ingestion-expanded.png`

The `ingestion` group expanded to show all six raw scraper assets, each
representing one source type on the Opportunity Party website:

- `raw_blog` — blog posts
- `raw_events` — events listing
- `raw_party_info` — governance / party-info documents
- `raw_team` — team profiles
- `raw_policies` — policy pages
- `raw_pdfs` — PDFs linked from policy pages

All six are green (healthy). The downstream `clean`, `site`, and
`validation` groups remain collapsed on the right, so the dependency
edges fan out from each ingestion asset to the groups that consume its
output. This view is useful when adding a new source — you can see at a
glance that the new `raw_*` asset wires correctly into `clean`.

These assets live in [`pipeline/defs/assets/ingestion.py`](../../pipeline/defs/assets/ingestion.py)
and follow the project's "raw data only when it has a downstream use" rule
(see [`AGENTS.md`](../../AGENTS.md)).

### 4. Lineage — `clean` group expanded

**File:** `04-lineage-clean-expanded.png`

The `clean` group expanded to show all eight normalization assets. The
fan-in to `clean_index` on the right is the cross-type search index
(`data/clean/_index.json`) that's regenerated each transform run.

Assets visible (one per ingestion source, plus the two composite
assets):

| Asset               | Input source      | Notes                          |
|---------------------|-------------------|--------------------------------|
| `apply_pdf_quirks`  | `clean_pdfs`      | Yellow chip — stale (see below)|
| `clean_pdfs`        | `raw_pdfs`        | PDF text extraction quirks     |
| `clean_blog`        | `raw_blog`        | Blog post normalisation        |
| `clean_events`      | `raw_events`      | Event listing                  |
| `clean_party_info`  | `raw_party_info`  | Governance docs                |
| `clean_policies`    | `raw_policies`    | Policy pages                   |
| `clean_team`        | `raw_team`        | Team profiles                  |
| `clean_index`       | All `clean_*`     | Cross-type search index        |

`apply_pdf_quirks` is the yellow chip from the overview (entry 2). It
sits downstream of `clean_pdfs` and applies per-document fix-ups — its
staleness is the trigger for the `validation` group to re-run
(see [`docs/pdf-pipeline.md`](../pdf-pipeline.md)).

### 5. Lineage — `validation` group expanded (fresh materialization)

**File:** `05-lineage-validation-expanded-fresh.png`

The same global lineage view as entry 2, but with the `validation` group
expanded. The two assets are now showing a fresh materialization:

- `validate_pdf_extraction` — Latest event: 2 minutes ago, Materialized
  16 Jul, 17:13. Has an Automation schedule.
- `write_pdf_pipeline_report` — Latest event: 2 minutes ago, Materialized
  16 Jul, 17:13. Has an Automation schedule.

Compare with entry 1 (16:23) — the validation group re-ran roughly 50
minutes later, presumably because the stale `apply_pdf_quirks` asset (see
entry 4) re-materialized and tripped the validation sensor. This
illustrates the "validation triggers off clean" design: the validation
group is downstream of `clean`, but its schedule is what makes the
freshness guarantee visible in the lineage view.

### 6. Lineage — `site` group expanded (failure chain visible)

**File:** `06-lineage-site-expanded.png`

The `site` group expanded to show the eight assets that build and deploy
the static site. The DAG shape is linear:

```
site_blog     ─┐
site_events   ─┤
site_party_info ─┼─► site_build ─► site_sitemap_resolved ─► site_deploy
site_policies ─┤
site_team     ─┘
```

Five per-source page-build assets feed into `site_build` (the Astro
build), then `site_sitemap_resolved` resolves URLs, then `site_deploy`
publishes to Cloudflare Workers.

**The three red assets at the end of the chain** are the failure mode
that motivated adding the `validation` group:

- `site_build` (red)
- `site_sitemap_resolved` (red)
- `site_deploy` (red)

The five upstream `site_*` assets are all green, so the failure is in
the build/deploy phase, not in content. `site_deploy` is deliberately
excluded from `full_pipeline` and only runs as part of `site_deploy_job`
because it pushes to production (see [`AGENTS.md`](../../AGENTS.md) —
"production-affecting assets must be excluded from `full_pipeline`").

### 7. Lineage — `site` group, detail cards expanded

**File:** `07-lineage-site-detail-cards.png`

Same view as entry 6, but each asset has its detail card open. The
"Latest event / Materialized" rows reveal the exact timeline of the
failure:

| Asset                    | Latest event   | Status      | When       |
|--------------------------|----------------|-------------|------------|
| `site_blog`              | 10 minutes ago | Materialized | 16 Jul 17:05 |
| `site_events`            | 10 minutes ago | Materialized | 16 Jul 17:05 |
| `site_party_info`        | 10 minutes ago | Materialized | 16 Jul 17:05 |
| `site_policies`          | 10 minutes ago | Materialized | 16 Jul 17:05 |
| `site_team`              | 10 minutes ago | Materialized | 16 Jul 17:05 |
| `site_build`             | —              | **Failed**  | 16 Jul 17:05 |
| `site_sitemap_resolved`  | —              | **Failed**  | 16 Jul 17:05 |
| `site_deploy`            | —              | **Failed**  | 16 Jul 17:05 |

All eight assets fired at the same minute, but only the build/deploy
phase failed. The Automation column shows each per-source asset has a
schedule attached, so they re-run independently of the build step. This
is the kind of view you use to decide whether to re-trigger `site_build`
in isolation rather than re-running the whole site group.

### 8. Asset detail — `site_build` failure

**File:** `08-asset-detail-site-build-failure.png`

The asset detail panel for `site_build`, opened from the lineage view by
selecting the failed node. Key fields:

- **Description:** "Run `astro build` to produce `site/dist/` from
  `site/src/content/`."
- **Status:** Run `dc712782` failed, and did not materialize this asset
  (with a `View logs` button to jump to the run).
- **Latest materialization:** "No materializations found" — i.e. no
  successful run since the last code reload.
- **Action button** (top): "Materialize selected" — the lineage view is
  in selection mode, so you can re-trigger just this asset and its
  downstream from the panel.

This is the typical triage view when `site_build` goes red: read the
description, click `View logs` to see the `astro build` output, fix the
upstream content or build config, then use `Materialize selected` to
re-run only the build/sitemap/deploy chain without re-scraping.

### 9. Runs — recent run history

**File:** `09-runs-list.png`

The **Runs** tab, filtered to "All". Lists the last 12 runs across the
project's jobs, sorted newest-first. Columns: ID, Target, Launched by,
Status, Created at, Duration.

Notable patterns:

- **Three `transforms_job` failures at 17:04** (`dc712782`, `643c310a`,
  `4dcc67eb`) — all manually launched, all failed within 6–7 seconds.
  This is the cluster that put `site_build` into the red state (entry 8).
- **`validation_job` runs repeatedly** at ~5 minute intervals (15:27,
  15:49, 16:23, 17:02, 17:07, 17:08, 17:13) — all manually launched but
  on a tight cadence, consistent with the `validation` group being
  driven by a sensor that watches the `clean` group.
- **`pdf_html_job` runs** appear at 17:02 and 17:13 (1 second each) —
  these convert cleaned PDF markdown into HTML for the static site.
- Tabs at the top: All, Backfills, Queued (0), In progress (0), Failed
  — useful for narrowing the view when something goes wrong.

> **Doc-vs-code drift note:** [`AGENTS.md`](../../AGENTS.md) lists the
> jobs as `ingestion_job / transforms_job / pdf_job`, but the UI here
> shows the actual job names as `transforms_job / validation_job /
> pdf_html_job` — i.e. `pdf_job` is named `pdf_html_job` in code, and
> there's an additional `validation_job` that AGENTS.md doesn't
> mention. If the docs drift further from the code, the **Jobs** page
> in the UI is the authoritative source.

### 10. Asset detail — `raw_blog` materialization

**File:** `10-asset-detail-raw-blog-materialization.png`

The asset detail panel for `raw_blog`, opened from the lineage view by
selecting the ingestion asset at the top of the column. Unlike entry 8
(`site_build` failure), this asset is healthy, so the panel surfaces
run metadata rather than a failure state.

- **Description:** "Scrape blog posts and save raw data to data/sources/."
- **Latest materialization:**
  - **Run:** `76a6e67b` (16 Jul, 10:44) — with a `View logs` button to
    jump to the run.
  - **item_count:** `20` — the number of blog items scraped in this
    run. Exposed as a metadata plot (single data point at value 20.0
    on 16 Jul 10:44) so future runs can be compared against it.
  - **output_path:**
    `/Users/max.collier/Projects/Max/vault/sms/projects/oppertunity-party/data/sources/opportunity-website/blog`
    — the canonical pointer to where raw scraped data lands. See
    [`docs/data-architecture.md`](../data-architecture.md) for the
    raw-vs-clean layer separation.

The lineage canvas on the left shows `raw_blog` selected (blue border)
at the top of the ingestion column, with `raw_events` (16 Jul, 10:44)
and `raw_party_info` (16 Jul, 10:45) visible below it — all green with
Automation schedules attached. This is the typical triage view when a
scraper's metadata looks off: read the description, check
`item_count` against the previous run, click `View logs` if the run
needs closer inspection, then re-materialise from the lineage view.