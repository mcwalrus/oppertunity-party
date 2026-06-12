# Unit 06 — Sensors: Event-Driven Runs

## What you will learn

- What a sensor is and how it differs from a schedule
- How to write a `@sensor` that polls an external source and emits `RunRequest`s
- How to use `run_key` to prevent duplicate runs
- How to use a cursor to track high-volume event streams efficiently
- How `@asset_sensor` triggers runs when a specific asset is materialized

## Why this unit exists

Schedules run on time. Sensors run on *events*. Real data pipelines are
event-driven: a file lands in S3, an upstream API updates, a partner dataset
refreshes. Without sensors you either poll with tight cron schedules (wasteful)
or build custom triggering logic outside Dagster. Sensors bring that logic
inside, make it observable, and give it access to Dagster's run management.

---

## 1. The sensor loop

A sensor function is called by the Dagster daemon on a configurable interval
(default: 30 seconds). Each evaluation:
1. Checks an external source (filesystem, API, database, another Dagster asset)
2. Yields zero or more `RunRequest` objects — each one triggers a job run
3. Optionally updates a cursor to remember where it left off

```
Dagster daemon                External source
      │                            │
      ├─── evaluate sensor ──────► │
      │◄── yield RunRequest(s) ────┤
      │
      └─── launches job run(s)
```

---

## 2. A basic file-system sensor

```python
import os
import dagster as dg

# Assume ingestion_job is defined elsewhere
from my_project.defs.jobs import ingestion_job

INBOX_DIR = "/data/inbox"

@dg.sensor(job=ingestion_job, minimum_interval_seconds=30)
def new_file_sensor(context: dg.SensorEvaluationContext):
    files = [f for f in os.listdir(INBOX_DIR) if f.endswith(".csv")]

    for filename in files:
        yield dg.RunRequest(
            run_key=filename,               # unique per file — prevents re-running the same file
            run_config={
                "ops": {
                    "raw_orders": {"config": {"filename": filename}}
                }
            },
        )
    # → emits one RunRequest per new CSV file; run_key deduplicates
```

`run_key` is the deduplication key: if the daemon has already seen a
`RunRequest` with `run_key="orders_2024-01-15.csv"`, it will not launch another
run for that file. This is how sensors avoid duplicate processing.

> **Surprises everyone coming from cron jobs:** There is no "don't trigger if
> already running" guard in a cron job — you build it yourself. Dagster's
> `run_key` gives you idempotency for free.

---

## 3. Sensor status: `SkipReason`

When there is nothing to do, return a `SkipReason` instead of yielding nothing.
This makes the sensor's inactivity visible in the UI (rather than appearing as
silent no-ops):

```python
@dg.sensor(job=ingestion_job)
def new_file_sensor(context: dg.SensorEvaluationContext):
    files = [f for f in os.listdir(INBOX_DIR) if f.endswith(".csv")]

    if not files:
        return dg.SkipReason("No new CSV files in inbox")
        # → UI shows "Skipped: No new CSV files in inbox"

    for filename in files:
        yield dg.RunRequest(run_key=filename)
```

---

## 4. Cursors for high-volume event streams

For ordered event streams (database sequences, message queue offsets, API
pagination), use a cursor to track the last processed position. The daemon
persists the cursor between evaluations:

```python
@dg.sensor(job=ingestion_job, minimum_interval_seconds=60)
def api_event_sensor(context: dg.SensorEvaluationContext):
    last_id = int(context.cursor or "0")   # cursor from previous evaluation

    new_events = fetch_events_after(last_id)   # your API call

    if not new_events:
        return dg.SkipReason(f"No events after id={last_id}")

    max_id = max(e["id"] for e in new_events)

    for event in new_events:
        yield dg.RunRequest(
            run_key=str(event["id"]),
            run_config={"ops": {"process_event": {"config": {"event_id": event["id"]}}}},
        )

    context.update_cursor(str(max_id))   # persist — daemon stores this between calls
    # → next evaluation starts from max_id, not 0
```

> **Analogy:** A cursor in Dagster sensors works exactly like a Kafka consumer
> offset — it marks where you left off so you don't reprocess old events.

---

## 5. `@asset_sensor` — trigger on asset materialization

`@asset_sensor` fires when a specific asset is materialized. It's the clean
way to trigger downstream pipelines when upstream data is ready:

```python
@dg.asset_sensor(
    asset_key=dg.AssetKey("cleaned_orders"),
    job=reporting_job,
)
def on_orders_ready(context: dg.SensorEvaluationContext, asset_event: dg.EventLogEntry):
    materialization = asset_event.dagster_event.step_materialization_data.materialization
    return dg.RunRequest(
        run_key=context.cursor,
        run_config={},
    )
    # → triggers reporting_job every time cleaned_orders is materialized
```

---

## 6. Enabling sensors

Like schedules, sensors are **off by default**. Enable them in the UI:

1. Start `dg dev`
2. Navigate to **Automation** → **Sensors**
3. Toggle your sensor **On**

The daemon then calls your sensor function every `minimum_interval_seconds`.

---

## Practical Exercises

1. **File sensor.** Create a temporary directory. Write a sensor that lists
   `.txt` files in it and yields a `RunRequest` for each. Toggle it on. Drop a
   file into the directory and watch the run appear. Drop the same file again
   — confirm no duplicate run (thanks to `run_key`).

2. **SkipReason.** Modify the sensor to return a `SkipReason` when the
   directory is empty. Observe the status change in the UI.

3. **Cursor sensor.** Simulate an ordered event source with a list and an
   index. Use `context.cursor` to track the last processed index. Confirm
   the sensor processes each "new" event exactly once across multiple
   evaluations.

4. **Asset sensor.** Write an `@asset_sensor` that fires when `cleaned_orders`
   is materialized, triggering a `reporting_job`. Materialize `cleaned_orders`
   manually and watch the reporting job launch automatically.

---

## Self-Check

1. A sensor fires every 30 seconds and finds 5 new files each time. After an
   hour, how many runs have been created — and why not more than 5 × 120?

2. What is the difference between `run_key` and `context.cursor`? When would
   you use each?

3. A sensor shows "Skipped" in the UI. Is that a problem? What does it mean?

---

## Key Takeaways

- Sensors poll on a configurable interval; they run on *events*, not time.
- `RunRequest(run_key=...)` is the mechanism to trigger a job run idempotently.
- `run_key` deduplicates: the same key never triggers a second run for the same
  sensor.
- `context.cursor` persists state between sensor evaluations — use it for
  ordered streams or pagination.
- `@asset_sensor` is the clean way to chain pipelines: "run B when A is done."
- Sensors are off by default; toggle on in **Automation → Sensors**.

## Next

[Unit 07 — Partitions & Backfills](../07-partitions-and-backfills/README.md)
