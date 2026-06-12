# Unit 01 — Foundations: The Asset Paradigm

## What you will learn

- Why Dagster models data assets instead of tasks, and what that changes
- How to scaffold a Dagster project with `create-dagster` and start the UI
- What the Dagster UI shows and how to read the asset graph
- The lifecycle: define → materialize → observe
- Where the key files live in a scaffolded project

## Why this unit exists

Every other unit builds on the mental model introduced here. If you skip it and
jump straight to writing `@asset` decorators, you'll be able to copy examples
but won't understand *why* Dagster is designed the way it is — and you'll hit
confusing walls when anything goes wrong. Five minutes on the paradigm saves
hours of cargo-culting later.

---

## 1. Task-centric vs. asset-centric orchestration

**The Airflow model (task-centric):** you define a DAG of *tasks* and wire them
with `>>` operators. The scheduler runs the tasks. The system has no opinion
about *what the tasks produce* — a task could write to S3, update a database, or
do nothing; the orchestrator doesn't know or care.

**The Dagster model (asset-centric):** you declare that *a thing should exist in
storage* — a table, a file, an ML model — and describe the function that
produces it. The orchestrator models the *data*, not the execution. The UI shows
you the data graph, not the task graph.

```
Airflow mindset:   "Run extract → run transform → run load"
Dagster mindset:   "raw_events exists, cleaned_events depends on it, report depends on cleaned_events"
```

**Where the analogy breaks down:** Dagster still executes Python functions
sequentially — it isn't magic. The difference is in what it *tracks* and
*exposes*. Dagster knows which asset is stale, which was last materialized at
`2024-01-15 09:32`, and which downstream assets are now out of date. Airflow
tracks task runs; Dagster tracks data state.

> **Surprises everyone coming from Airflow:** In Airflow, a DAG run is the
> primary observable unit. In Dagster, a *materialization* of an asset is. You
> will find yourself asking "when was `orders_cleaned` last materialized?" rather
> than "did the `etl_dag` run succeed?"

---

## 2. Scaffold a project and start the UI

> Grounded in: [docs.dagster.io/getting-started/installation](https://docs.dagster.io/getting-started/installation), Dagster 1.13.9

```bash
# Scaffold (uv recommended — manages the venv automatically)
uvx create-dagster@latest project my-dagster-project
# → respond y to run uv sync

cd my-dagster-project
source .venv/bin/activate

# Start the Dagster webserver + daemon in one command
dg dev
# → Dagster UI available at http://localhost:3000
```

Open `http://localhost:3000`. You should see the **Asset Graph** — a visual map
of the demo assets that `create-dagster` scaffolded for you.

```
Expected output in the terminal:
  Serving dagster-webserver on http://127.0.0.1:3000 in process ...
  dagster - INFO - Launching Dagster daemon process.
```

---

## 3. The scaffolded project layout

```
my-dagster-project/
├── pyproject.toml          # project metadata + Dagster entry point
├── uv.lock                 # locked dependency tree
└── src/
    └── my_dagster_project/
        ├── __init__.py
        ├── definitions.py  # ← THE entry point Dagster loads
        └── defs/
            └── __init__.py # ← assets, resources, schedules live here
```

The critical file is `definitions.py`. It exports a `Definitions` object — the
contract between your code and the Dagster runtime. You'll learn what goes in it
in Unit 03.

> **Surprises everyone coming from Airflow:** There is no `dags/` folder where
> you drop files and Airflow picks them up. In Dagster, everything flows through
> a single explicit `Definitions` object in a known Python module.

---

## 4. The asset lifecycle: define → materialize → observe

An **asset** in Dagster has three distinct states:

| State | Meaning |
|-------|---------|
| **Defined** | The `@asset` function exists in code; Dagster knows about it |
| **Materialized** | The function ran and its output was saved to storage |
| **Stale** | An upstream asset was re-materialized; this one hasn't been re-run yet |

In the UI, assets appear gray (never materialized), green (materialized, fresh),
or yellow (stale — upstream has changed). This gives you data-state visibility
that a task-based system can't provide.

---

## 5. What `dg dev` runs under the hood

`dg dev` starts two processes:

- **Dagster webserver** — serves the UI at `localhost:3000`; reads your
  `Definitions` object to build the UI; does not execute assets
- **Dagster daemon** — the background worker that executes schedules, sensors,
  and run requests

Both processes watch for code changes. In dev mode you don't need to restart
when you change an asset.

---

## Practical Exercises

1. **Scaffold and explore.** Run the scaffold commands above. Navigate to
   `http://localhost:3000` → Assets tab. Click on any demo asset. Note the
   "Materialization" tab — it is empty until you materialize it.

2. **Materialize a demo asset.** In the UI, click an asset → "Materialize".
   Watch the run page. Return to the asset page — the "Latest Materialization"
   section should now show a timestamp.

3. **Find the definitions file.** Open `src/my_dagster_project/definitions.py`
   in your editor. Note what it imports and what it passes to `Definitions()`.
   You don't need to understand it yet — just orient yourself.

4. **Break it (safely).** Introduce a Python syntax error in any `defs/` file,
   save it, and refresh the UI. Observe the error banner. Fix the error and
   watch the UI recover automatically.

---

## Self-Check

1. In Airflow a "run" is attached to a DAG. In Dagster, what is the primary
   observable unit that a run is attached to?

2. What two processes does `dg dev` start, and what is each one responsible for?

3. An asset is shown yellow in the UI. What does that mean about the
   *relationship* between this asset and its upstream dependency?

---

## Key Takeaways

- Dagster models *data assets* (tables, files, models), not tasks. The
  scheduler asks "what is stale?" not "what is scheduled?"
- `dg dev` starts both the webserver (UI) and the daemon (execution) in one
  command.
- A scaffolded project has one entry point: `definitions.py`, which exports a
  `Definitions` object.
- Assets move through three observable states: defined → materialized → stale.
- The UI is a *data graph*, not a task graph. Each node is a persistent artifact.

## Next

[Unit 02 — Software-Defined Assets](../02-software-defined-assets/README.md)
