# Unit 05 — Jobs & Schedules

## What you will learn

- What a Dagster job is and how it relates to assets
- How to define an asset job that targets a selection of assets
- How to write a `@schedule` with a cron expression
- How to use `build_schedule_from_partitioned_job` for partition-aware schedules
- How to manually trigger a job from the UI and CLI

## Why this unit exists

Assets don't run themselves. Jobs and schedules are the execution layer: a job
defines *what* to run, and a schedule defines *when*. Understanding this
separation — asset graph vs. execution trigger — prevents the confusion of
"I defined an asset, why doesn't it run every day?"

---

## 1. What is a job?

A **job** in Dagster is an executable subset of the asset graph, packaged as a
named, re-runnable unit. Jobs are the handle you attach schedules and sensors to.

> **Analogy to Airflow:** A job is like a DAG — the named thing you schedule,
> trigger manually, and monitor. The difference: a Dagster job *selects* from
> the asset graph rather than defining a new graph from scratch. The assets
> already exist; the job is just a lens over them.

---

## 2. Defining a job with `define_asset_job`

```python
import dagster as dg

@dg.asset(group_name="ingestion")
def raw_orders():
    return [{"id": 1, "amount": 100}]

@dg.asset(group_name="ingestion")
def cleaned_orders(raw_orders):
    return [o for o in raw_orders if o["amount"] > 0]

@dg.asset(group_name="reporting")
def orders_report(cleaned_orders):
    return {"total": sum(o["amount"] for o in cleaned_orders)}

# Job selects all assets in the "ingestion" group
ingestion_job = dg.define_asset_job(
    name="ingestion_job",
    selection=dg.AssetSelection.groups("ingestion"),
)

# Job selects specific assets by key
full_pipeline_job = dg.define_asset_job(
    name="full_pipeline_job",
    selection=dg.AssetSelection.all(),
)

defs = dg.Definitions(
    assets=[raw_orders, cleaned_orders, orders_report],
    jobs=[ingestion_job, full_pipeline_job],
)
```

`AssetSelection` is expressive:

```python
dg.AssetSelection.all()                          # every asset
dg.AssetSelection.groups("ingestion")            # all assets in a group
dg.AssetSelection.assets("orders_report")        # one asset by key
dg.AssetSelection.assets("orders_report").upstream()   # asset + all upstream deps
```

---

## 3. Defining a schedule with `@schedule`

A schedule attaches a cron expression to a job. At each tick, it emits a
`RunRequest` that causes the job to run:

```python
import dagster as dg

@dg.schedule(
    job=ingestion_job,
    cron_schedule="0 6 * * *",    # every day at 06:00 UTC
)
def daily_ingestion_schedule(context: dg.ScheduleEvaluationContext):
    return dg.RunRequest(run_key=None)
    # → triggers ingestion_job every day at 06:00

defs = dg.Definitions(
    assets=[raw_orders, cleaned_orders, orders_report],
    jobs=[ingestion_job, full_pipeline_job],
    schedules=[daily_ingestion_schedule],
)
```

**Common cron patterns:**

```
"0 * * * *"       every hour at :00
"0 6 * * *"       daily at 06:00 UTC
"0 6 * * 1"       every Monday at 06:00 UTC
"*/15 * * * *"    every 15 minutes
"0 6 1 * *"       first of every month at 06:00 UTC
```

> **Surprises everyone coming from Airflow:** Dagster schedules are **off by
> default**. After adding a schedule to `Definitions` and reloading the UI, you
> must explicitly toggle it **on** in the UI under Automation → Schedules. This
> prevents accidentally running schedules in dev environments.

---

## 4. Enabling a schedule in the UI

1. Start `dg dev`
2. Navigate to **Automation** → **Schedules** in the left sidebar
3. Find your schedule name
4. Toggle the switch to **On**

The schedule will fire on its next cron tick. You can also click **"Test
schedule"** to evaluate it immediately without waiting for the cron window.

---

## 5. Simpler schedules with `ScheduleDefinition`

For schedules that always run the job with no custom logic, skip the decorator:

```python
daily_schedule = dg.ScheduleDefinition(
    name="daily_ingestion_schedule",
    job=ingestion_job,
    cron_schedule="0 6 * * *",
)
```

This is preferred for straightforward cases — the decorator form is only needed
when you want to customise `RunRequest` config per tick (e.g., pass a date as
run config).

---

## 6. Triggering a job from the CLI

```bash
# Execute a job immediately (bypasses schedule, runs in foreground)
dagster job execute -j ingestion_job

# Execute targeting specific assets
dagster asset materialize --select raw_orders cleaned_orders
```

---

## 7. Run config — parameterising a job at runtime

Jobs can accept structured config at launch. This is useful for passing dates,
feature flags, or processing modes:

```python
import dagster as dg
from pydantic import BaseModel

class IngestionConfig(dg.Config):
    batch_size: int = 1000
    dry_run: bool = False

@dg.asset
def raw_orders(config: IngestionConfig):
    print(f"Batch size: {config.batch_size}, dry_run={config.dry_run}")
    return []

# Launch with config from the UI "Launchpad" or via CLI:
# dagster job execute -j ingestion_job --config '{"ops": {"raw_orders": {"config": {"batch_size": 500}}}}'
```

---

## Practical Exercises

1. **Define two jobs.** Create `ingestion_job` (selects the `ingestion` group)
   and `full_pipeline_job` (selects all). Register both. Confirm they appear
   under **Jobs** in the UI.

2. **Write a schedule.** Attach a `@schedule` to `ingestion_job` with cron
   `"* * * * *"` (every minute). Toggle it on in the UI. Watch it fire and
   produce runs.

3. **Simplify with `ScheduleDefinition`.** Replace the decorated schedule with
   a `ScheduleDefinition` equivalent. Confirm behaviour is identical.

4. **Add run config.** Add a `Config` class to one of your assets. Launch the
   job from the UI Launchpad — observe the config schema shown there.

---

## Self-Check

1. An asset appears in the asset graph but never runs on your daily schedule.
   What are the two most likely causes?

2. What is the difference between `AssetSelection.groups("x")` and
   `AssetSelection.all().downstream_of("raw_orders")`?

3. `ScheduleDefinition` vs `@schedule` — when would you choose the decorator?

---

## Key Takeaways

- A job is a named, re-runnable selection of assets — the handle for scheduling
  and monitoring.
- `define_asset_job` uses `AssetSelection` to pick which assets the job covers.
- `@schedule` / `ScheduleDefinition` attaches a cron expression to a job; use
  the class form for simple cases, the decorator for custom per-tick logic.
- Dagster schedules are **off by default** — toggle them on in the UI.
- `dg.Config` lets jobs accept structured, typed run configuration at launch.

## Next

[Unit 06 — Sensors: Event-Driven Runs](../06-sensors/README.md)
