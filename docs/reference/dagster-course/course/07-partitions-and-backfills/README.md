# Unit 07 — Partitions & Backfills

## What you will learn

- What a partition is and why it makes large pipelines incremental
- How to define time-based partitions with `DailyPartitionsDefinition`
- How to access the current partition key inside an asset
- How to run a backfill over a range of historical partitions
- Static partitions (by category) and when to choose them over time-based

## Why this unit exists

Without partitions, re-running a pipeline processes all history every time. A
`daily_orders` asset that covers two years of data runs for 730 rows on January
1 and for 731 rows on January 2. With partitions, each day is an independent
slice — you run January 2 once, and if it fails, you re-run only January 2, not
all of history. This unit unlocks incremental processing, targeted retries, and
historical backfills.

---

## 1. What is a partition?

A **partition** is a logical slice of an asset. An asset with a
`DailyPartitionsDefinition` is not one asset — it is a collection of `N`
independent assets, one per day. Each slice can be materialized, re-materialized,
or skipped independently.

```
orders asset (partitioned by day)
  └── 2024-01-01   ← one materialization
  └── 2024-01-02   ← a separate, independent materialization
  └── 2024-01-03   ← can be re-run without touching 01 or 02
  └── ...
```

In the UI, a partitioned asset shows a grid of colored cells — green for
materialized partitions, gray for missing ones.

---

## 2. `DailyPartitionsDefinition`

```python
import dagster as dg
from datetime import datetime

daily_partitions = dg.DailyPartitionsDefinition(start_date="2024-01-01")

@dg.asset(partitions_def=daily_partitions)
def daily_orders(context: dg.AssetExecutionContext):
    partition_key = context.partition_key          # e.g. "2024-01-15"
    date = datetime.strptime(partition_key, "%Y-%m-%d")

    # Fetch only data for this date
    orders = fetch_orders_for_date(date)           # your query, parameterised by date

    context.add_output_metadata({"row_count": len(orders), "date": partition_key})
    return orders
    # → when materializing "2024-01-15", only Jan 15 data is fetched
```

> **Surprises everyone coming from cron jobs:** A cron job just runs "now" — it
> has no concept of *which slice* it's processing. In Dagster, the partition key
> is a first-class value that flows into every asset and can be used to
> parameterise queries, filenames, and API calls.

---

## 3. Downstream assets inherit the partition

If a downstream asset depends on a partitioned asset, Dagster automatically
aligns them partition-for-partition:

```python
@dg.asset(partitions_def=daily_partitions)
def daily_orders(context: dg.AssetExecutionContext):
    return fetch_orders_for_date(context.partition_key)

@dg.asset(partitions_def=daily_partitions)
def daily_revenue(daily_orders, context: dg.AssetExecutionContext):
    # daily_orders here is the value for *the same partition key*
    return sum(o["amount"] for o in daily_orders)
    # → materializing "2024-01-15" for daily_revenue loads daily_orders["2024-01-15"]
```

You don't have to do anything special — Dagster aligns partition keys
automatically when both assets share the same `PartitionsDefinition`.

---

## 4. Other partition types

**Weekly:**

```python
weekly_partitions = dg.WeeklyPartitionsDefinition(start_date="2024-01-01")
```

**Hourly:**

```python
hourly_partitions = dg.HourlyPartitionsDefinition(start_date="2024-01-01-00:00")
```

**Static — for non-time categories:**

```python
region_partitions = dg.StaticPartitionsDefinition(["us-east", "eu-west", "ap-south"])

@dg.asset(partitions_def=region_partitions)
def regional_summary(context: dg.AssetExecutionContext):
    region = context.partition_key    # "us-east", "eu-west", or "ap-south"
    return aggregate_for_region(region)
```

Use static partitions when your slices are categories (regions, environments,
customer tiers) rather than time intervals.

**Monthly:**

```python
monthly_partitions = dg.MonthlyPartitionsDefinition(start_date="2024-01-01")
```

---

## 5. Running a backfill

A backfill materializes a range of historical partitions. From the UI:

1. Navigate to **Assets** → select a partitioned asset
2. Click **"Materialize"** → **"Select partitions"**
3. Choose a date range (e.g., all of January 2024)
4. Click **Launch backfill**

Dagster queues one run per partition (or batches them depending on concurrency
config). Each run only touches its own partition slice.

From the CLI:

```bash
dagster asset backfill --asset daily_orders \
  --partition-range-start "2024-01-01" \
  --partition-range-end "2024-01-31"
# → queues 31 runs, one per day
```

> **Tip:** Set `max_retries=2` on your job to automatically retry failed
> partition runs without re-running the whole backfill.

---

## 6. Partition-aware schedules

Schedule a job to run for "the most recent complete partition" (e.g., yesterday):

```python
daily_job = dg.define_asset_job(
    name="daily_orders_job",
    selection=dg.AssetSelection.assets("daily_orders"),
    partitions_def=daily_partitions,
)

daily_schedule = dg.build_schedule_from_partitioned_job(
    job=daily_job,
    hour_of_day=1,     # run at 01:00 UTC, targeting yesterday's partition
    minute_of_hour=0,
)
```

`build_schedule_from_partitioned_job` creates a schedule that automatically
selects the most recent complete partition at each tick — you don't need to
compute the partition key in the schedule function.

---

## Practical Exercises

1. **Daily partition.** Define `daily_orders` with `DailyPartitionsDefinition`
   (start `2024-01-01`). Open the UI — see the partition grid. Materialize a
   single partition ("2024-01-05"). Confirm only that cell turns green.

2. **Downstream alignment.** Add `daily_revenue` that depends on
   `daily_orders`. Materialize `daily_revenue` for the same date. Observe in
   the run log that `daily_orders["2024-01-05"]` was loaded as input.

3. **Static partitions.** Define a `regional_summary` asset with regions
   `["us", "eu", "apac"]`. Materialize all three. Confirm three independent
   materializations appear in the UI.

4. **Backfill.** Trigger a backfill of `daily_orders` for a 7-day range.
   Watch the run queue. After completion, count how many runs were created.

---

## Self-Check

1. You have `daily_orders` and `daily_revenue`, both using the same
   `DailyPartitionsDefinition`. You materialize `daily_revenue` for
   `"2024-01-10"`. Which partition of `daily_orders` does Dagster load as
   input?

2. What is the difference between running a backfill and running the daily
   schedule for 30 days? Are the results the same?

3. You add a new region `"sa-east"` to a `StaticPartitionsDefinition`. What
   do you need to do to materialize it?

---

## Key Takeaways

- A partition is an independent, re-runnable slice of an asset — one
  materialization per slice.
- `context.partition_key` gives the current slice's identifier inside the asset
  function — use it to parameterise queries and filenames.
- Downstream assets with the same `PartitionsDefinition` are aligned
  automatically — no extra wiring needed.
- Backfills queue one run per partition; they enable historical processing
  without changing asset logic.
- Use `build_schedule_from_partitioned_job` for "run the latest complete
  partition on a schedule" — the most common production pattern.

## Next

[Unit 08 — Testing & Asset Checks](../08-testing-and-checks/README.md)
