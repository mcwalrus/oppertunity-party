# Dagster: Asset-Centric Data Orchestration

A ground-up course for Python engineers who have shipped task-based pipelines
(Airflow, cron, dbt standalone, or Prefect) and want to understand Dagster's
asset-first model — from first principles to production patterns.

Each unit depends only on earlier ones. You can stop after any unit and have a
working mental model. Units 01–03 are non-skippable foundations.

---

## Course Structure

| Unit | Topic | Practical goal |
|------|-------|----------------|
| [01](course/01-asset-paradigm/README.md) | Foundations: The Asset Paradigm | Scaffold a project with `create-dagster`, open the UI, explain the paradigm shift |
| [02](course/02-software-defined-assets/README.md) | Software-Defined Assets | Write `@asset`, express upstream deps as function args, materialize from the UI |
| [03](course/03-definitions-and-structure/README.md) | The Definitions Object & Project Structure | Wire assets into `Definitions`; understand code locations and the `defs/` layout |
| [04](course/04-resources/README.md) | Resources: Managed External Connections | Define `ConfigurableResource`, inject DB/API clients, configure per-environment |
| [05](course/05-jobs-and-schedules/README.md) | Jobs & Schedules | Group assets into jobs; automate with `@schedule` and cron intervals |
| [06](course/06-sensors/README.md) | Sensors: Event-Driven Runs | React to external events using `@sensor` and `RunRequest` |
| [07](course/07-partitions-and-backfills/README.md) | Partitions & Backfills | Slice an asset by time; run targeted backfills |
| [08](course/08-testing-and-checks/README.md) | Testing & Asset Checks | Unit-test assets by direct invocation; enforce data quality with `@asset_check` |
| [09](course/09-production-patterns/README.md) | Production Patterns | IO managers, metadata, multi-code-location deployments, Dagster+ |

---

## Prerequisites

**You need:**
- Python 3.10+ (3.13 recommended)
- Comfort with Python functions, decorators, and virtual environments
- Basic familiarity with SQL or dataframes (you write queries; you don't need to know Dagster)
- Passing exposure to any task-based pipeline tool (Airflow, cron, Prefect, Make) — even conceptually

**You do NOT need:**
- Prior Dagster experience
- Knowledge of Kubernetes, Docker, or cloud infra (those come in Unit 09)
- Any specific database — examples use in-memory data; swap in Postgres/Snowflake when you're ready

---

## Installation & Setup

> Source: [docs.dagster.io/getting-started/installation](https://docs.dagster.io/getting-started/installation) — Dagster 1.13.9

**Recommended path: `uv` + `create-dagster`**

```bash
# 1. Install uv (the recommended Python package manager for Dagster)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Scaffold a new project (uvx runs create-dagster without a global install)
uvx create-dagster@latest project my-dagster-project
# → respond y to run uv sync after scaffolding

# 3. Activate the virtual environment
cd my-dagster-project
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows

# 4. Verify
dg --version
# → dg 0.x.x

# 5. Launch the Dagster UI
dg dev
# → Open http://localhost:3000 in your browser
```

**Alternative: pip (no uv)**

```bash
# Install create-dagster via pip
pip install create-dagster

# Scaffold project
create-dagster project my-dagster-project
cd my-dagster-project

python -m venv .venv
source .venv/bin/activate
pip install --editable ".[dev]"

dg dev
```

**Verify the UI is working:** navigate to `http://localhost:3000` — you should see the Dagster asset graph with the scaffolded demo assets.

---

## Core Mental Models (Read Before Unit 1)

> These are the five load-bearing ideas. Everything else in the course hangs off them.

### 1. The unit of work is data, not a task

In Airflow you declare *"run these tasks in this order."* In Dagster you declare
*"these data assets exist and here is how to produce them."* The scheduler asks
**"which assets need updating?"** not **"which tasks are scheduled?"**

This inversion changes how you think about lineage, retries, and observability:
instead of debugging a failed task, you ask *"which asset is stale and why?"*

### 2. `Definitions` is the deployment contract

Every Dagster abstraction — assets, resources, schedules, sensors — must be
registered in a top-level `Definitions` object. That object is what the Dagster
webserver and daemon load. **If it isn't in `Definitions`, it doesn't exist.**

### 3. Resources are injected, not imported

External connections (Snowflake client, S3 bucket, API key) are declared as
`ConfigurableResource`s and injected into assets at runtime. The same asset code
runs against a mock resource in tests and a real connection in prod — zero
branching logic in your pipeline.

### 4. Materialization = compute + persist + record

Running an `@asset` function and saving its output is called *materializing* the
asset. Dagster records every materialization: when it ran, duration, any
attached metadata (row counts, schemas). This is your audit trail.

### 5. Partitions turn one asset into N independent slices

A partitioned asset can be materialized one slice at a time. A
`DailyPartitionsDefinition` lets you process `2024-01-01` independently of
`2024-01-02` — enabling incremental pipelines and targeted backfills without
changing your asset logic.

---

## Recommended Sequence

**Phase 1 — Foundations (non-skippable): Units 01–03**
Spend the most time here. These three units establish the mental model that
everything else builds on. Unit 01 is conceptual; Units 02–03 are hands-on.

**Phase 2 — Core building blocks: Units 04–06**
Resources, jobs, schedules, and sensors are independent of each other but all
depend on the Definitions model from Phase 1. You can read 04–06 in any order.

**Phase 3 — Scale and quality: Units 07–08**
Partitions (07) and testing/checks (08) are independent; do 07 first if you
have incremental-processing use cases, 08 first if you need to ship tests today.

**Phase 4 — Production: Unit 09**
IO managers, metadata, and deployment patterns. Read after you have working
pipelines you want to harden.

---

## Key Reference Commands

```bash
# ── PROJECT ──────────────────────────────────────────────────────────────
uvx create-dagster@latest project <name>   # scaffold a new project
dg dev                                      # start UI + daemon (dev mode)
dg --version                                # print installed version

# ── SCAFFOLD ASSETS / CHECKS ─────────────────────────────────────────────
dg scaffold defs dagster.asset defs/my_asset.py   # scaffold an asset file
dg scaffold defs dagster.schedule defs/schedule.py

# ── MATERIALIZATION (CLI) ─────────────────────────────────────────────────
# Most materialization happens via the UI; CLI equivalents:
dagster asset materialize --select my_asset        # materialize one asset
dagster asset materialize --select "*"             # materialize all assets
dagster job execute -j my_job                      # execute a named job

# ── TESTING ──────────────────────────────────────────────────────────────
pytest tests/                                      # run all tests
pytest tests/ -k test_my_asset                     # run one test
```
