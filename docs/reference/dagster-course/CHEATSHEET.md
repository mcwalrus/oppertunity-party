# Dagster Cheatsheet

> Dagster 1.13.9 · Python 3.13 · `import dagster as dg`

---

```
# ── SETUP & PROJECT ──────────────────────────────────────────────────────────

# Install uv (recommended package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Scaffold a new project
uvx create-dagster@latest project my-project

# Activate venv and verify
cd my-project && source .venv/bin/activate
dg --version                          # → dg 0.x.x

# Start the webserver + daemon (dev mode)
dg dev                                # → http://localhost:3000

# Start with a multi-code-location workspace file
dagster dev -w workspace.yaml

# ── SCAFFOLDING ──────────────────────────────────────────────────────────────

dg scaffold defs dagster.asset src/my_project/defs/my_asset.py
dg scaffold defs dagster.schedule src/my_project/defs/schedules.py
dg scaffold defs dagster.sensor src/my_project/defs/sensors.py

# ── MATERIALIZATION (CLI) ─────────────────────────────────────────────────────

dagster asset materialize --select my_asset
dagster asset materialize --select "group:ingestion"   # all in a group
dagster asset materialize --select "*"                 # all assets
dagster job execute -j my_job
dagster asset backfill --asset daily_orders \
  --partition-range-start "2024-01-01" \
  --partition-range-end   "2024-01-31"

# ── TESTING ──────────────────────────────────────────────────────────────────

pytest tests/
pytest tests/ -k test_my_asset
```

---

```python
# ── ASSETS ───────────────────────────────────────────────────────────────────

import dagster as dg

# Minimal asset
@dg.asset
def raw_data():
    return [1, 2, 3]

# Asset with upstream dependency (argument name = upstream asset key)
@dg.asset
def cleaned_data(raw_data):
    return [x for x in raw_data if x > 0]

# Asset with context + metadata
@dg.asset
def enriched_data(context: dg.AssetExecutionContext, cleaned_data):
    context.add_output_metadata({"row_count": len(cleaned_data)})
    return cleaned_data

# Asset with group + key prefix
@dg.asset(group_name="ingestion", key_prefix=["warehouse", "raw"])
def raw_orders():
    return []                         # key: warehouse/raw/raw_orders

# Dependency without value passing
@dg.asset(deps=["load_to_db"])
def downstream():                     # ordered after load_to_db; doesn't receive its output
    ...

# Multi-asset: one function → multiple assets
@dg.multi_asset(specs=[dg.AssetSpec("users"), dg.AssetSpec("sessions")])
def fetch_analytics():
    return [{"id": 1}], [{"user_id": 1}]
```

---

```python
# ── DEFINITIONS ───────────────────────────────────────────────────────────────

import dagster as dg
from my_project import defs as defs_pkg

defs = dg.Definitions(
    assets=dg.load_assets_from_package_module(defs_pkg),
    resources={"db": MyDatabaseResource(...)},
    jobs=[my_job],
    schedules=[my_schedule],
    sensors=[my_sensor],
)

# Load from multiple modules
defs = dg.Definitions(
    assets=dg.load_assets_from_modules([ingestion_assets, transform_assets]),
)

# Merge sub-package definitions
defs = dg.Definitions.merge(ingestion.defs, transforms.defs, reporting.defs)
```

---

```python
# ── RESOURCES ─────────────────────────────────────────────────────────────────

import dagster as dg

class WarehouseResource(dg.ConfigurableResource):
    host: str
    password: str

    def query(self, sql: str):
        ...                            # returns results from warehouse

# Wire in definitions
defs = dg.Definitions(
    assets=[...],
    resources={
        "warehouse": WarehouseResource(
            host=dg.EnvVar("WH_HOST"),         # resolved at runtime, not import
            password=dg.EnvVar("WH_PASSWORD"),
        ),
    },
)

# Use in an asset (parameter name must match Definitions key)
@dg.asset
def orders(warehouse: WarehouseResource):
    return warehouse.query("SELECT * FROM orders")

# Test with a fake
class FakeWarehouse(WarehouseResource):
    def query(self, sql: str):
        return [{"id": 1}]

result = orders(warehouse=FakeWarehouse(host="x", password="x"))
```

---

```python
# ── JOBS & ASSET SELECTION ───────────────────────────────────────────────────

import dagster as dg

ingestion_job = dg.define_asset_job(
    name="ingestion_job",
    selection=dg.AssetSelection.groups("ingestion"),
)

# Common selection expressions
dg.AssetSelection.all()
dg.AssetSelection.groups("g1", "g2")
dg.AssetSelection.assets("my_asset")
dg.AssetSelection.assets("my_asset").upstream()          # asset + all its deps
dg.AssetSelection.assets("my_asset").downstream()        # asset + everything downstream
```

---

```python
# ── SCHEDULES ────────────────────────────────────────────────────────────────

import dagster as dg

# Simple schedule (preferred for no-customisation cases)
daily_schedule = dg.ScheduleDefinition(
    name="daily_ingestion",
    job=ingestion_job,
    cron_schedule="0 6 * * *",      # daily at 06:00 UTC
)

# Schedule with custom logic (use @schedule decorator)
@dg.schedule(job=ingestion_job, cron_schedule="0 6 * * *")
def daily_schedule(context: dg.ScheduleEvaluationContext):
    return dg.RunRequest(
        run_key=str(context.scheduled_execution_time),
        tags={"env": "prod"},
    )

# Partition-aware schedule (most common production pattern)
daily_partitioned_job = dg.define_asset_job(
    "daily_job",
    selection=dg.AssetSelection.assets("daily_orders"),
    partitions_def=dg.DailyPartitionsDefinition(start_date="2024-01-01"),
)
auto_schedule = dg.build_schedule_from_partitioned_job(
    job=daily_partitioned_job, hour_of_day=1
)

# Common cron patterns
# "0 * * * *"    every hour
# "0 6 * * *"    daily 06:00
# "0 6 * * 1"    weekly Monday 06:00
# "*/15 * * * *" every 15 min
# "0 6 1 * *"    monthly 1st at 06:00

# ⚠ Schedules are OFF by default — toggle on in UI: Automation → Schedules
```

---

```python
# ── SENSORS ───────────────────────────────────────────────────────────────────

import dagster as dg

@dg.sensor(job=my_job, minimum_interval_seconds=30)
def file_sensor(context: dg.SensorEvaluationContext):
    files = list_new_files()
    if not files:
        return dg.SkipReason("No new files")     # visible in UI

    for f in files:
        yield dg.RunRequest(
            run_key=f,                            # deduplicates — same key never re-runs
            run_config={...},
        )

# Cursor sensor for ordered streams
@dg.sensor(job=my_job)
def cursor_sensor(context: dg.SensorEvaluationContext):
    last_id = int(context.cursor or "0")
    events = fetch_events_after(last_id)
    if not events:
        return dg.SkipReason(f"No events after {last_id}")
    for e in events:
        yield dg.RunRequest(run_key=str(e["id"]))
    context.update_cursor(str(max(e["id"] for e in events)))

# Asset sensor — fire when an asset is materialized
@dg.asset_sensor(asset_key=dg.AssetKey("cleaned_orders"), job=reporting_job)
def on_orders_ready(context, asset_event):
    return dg.RunRequest(run_key=context.cursor)

# ⚠ Sensors are OFF by default — toggle on in UI: Automation → Sensors
```

---

```python
# ── PARTITIONS ────────────────────────────────────────────────────────────────

import dagster as dg

# Time-based
daily   = dg.DailyPartitionsDefinition(start_date="2024-01-01")
weekly  = dg.WeeklyPartitionsDefinition(start_date="2024-01-01")
hourly  = dg.HourlyPartitionsDefinition(start_date="2024-01-01-00:00")
monthly = dg.MonthlyPartitionsDefinition(start_date="2024-01-01")

# Static (categories)
regions = dg.StaticPartitionsDefinition(["us-east", "eu-west", "ap-south"])

# Partitioned asset
@dg.asset(partitions_def=daily)
def daily_orders(context: dg.AssetExecutionContext):
    date = context.partition_key      # e.g. "2024-01-15"
    return fetch_orders(date)

# Backfill CLI
# dagster asset backfill --asset daily_orders \
#   --partition-range-start "2024-01-01" \
#   --partition-range-end   "2024-01-31"
```

---

```python
# ── TESTING ───────────────────────────────────────────────────────────────────

import dagster as dg

# 1. Call asset directly (no Dagster machinery needed)
result = my_asset(upstream_dep=[1, 2, 3])

# 2. Call with resources (pass instances directly)
result = my_asset(db=FakeDatabase(connection_string="fake://"))

# 3. Build context (for partition_key, metadata, log)
ctx = dg.build_asset_context(
    partition_key="2024-01-15",
    input_values={"upstream": [{"id": 1}]},
)
result = my_asset(context=ctx)

# 4. Test an asset check
check_result = my_check(orders=[{"id": 1, "amount": 100}])
assert check_result.passed
```

---

```python
# ── ASSET CHECKS ─────────────────────────────────────────────────────────────

import dagster as dg

@dg.asset_check(asset=orders)
def orders_not_empty(orders) -> dg.AssetCheckResult:
    return dg.AssetCheckResult(
        passed=len(orders) > 0,
        metadata={"row_count": len(orders)},
    )

@dg.asset_check(asset=orders)
def no_nulls(orders) -> dg.AssetCheckResult:
    nulls = [o for o in orders if o.get("amount") is None]
    return dg.AssetCheckResult(
        passed=len(nulls) == 0,
        severity=dg.AssetCheckSeverity.WARN,   # WARN = downstream proceeds; ERROR = downstream blocked
        metadata={"null_count": len(nulls)},
    )

# Register in Definitions
defs = dg.Definitions(assets=[orders], asset_checks=[orders_not_empty, no_nulls])
```

---

```python
# ── IO MANAGERS ───────────────────────────────────────────────────────────────

import dagster as dg

# Built-in: in-memory (default, dev only)
# Built-in: local filesystem
defs = dg.Definitions(assets=[...], resources={"io_manager": dg.fs_io_manager})

# S3 (install: pip install dagster-aws)
from dagster_aws.s3 import S3PickleIOManager, S3Resource
defs = dg.Definitions(
    assets=[...],
    resources={
        "io_manager": S3PickleIOManager(
            s3_resource=S3Resource(),
            s3_bucket=dg.EnvVar("S3_BUCKET"),
        ),
    },
)

# Custom IO Manager
class MyIOManager(dg.IOManager):
    def handle_output(self, context: dg.OutputContext, obj):
        ...   # save obj to storage
    def load_input(self, context: dg.InputContext):
        ...   # load and return object from storage
```

---

```python
# ── METADATA ─────────────────────────────────────────────────────────────────

context.add_output_metadata({
    "row_count":            dg.MetadataValue.int(1000),
    "preview":              dg.MetadataValue.md(df.head().to_markdown()),
    "source_url":           dg.MetadataValue.url("https://api.example.com"),
    "schema":               dg.MetadataValue.json({"col": "type"}),
    "dagster/column_schema": dg.TableSchema(
        columns=[dg.TableColumn("id", "int"), dg.TableColumn("name", "str")]
    ),
})
```

---

```python
# ── PRODUCTION: RETRIES & CONCURRENCY ────────────────────────────────────────

# Asset-level retry
@dg.asset(retry_policy=dg.RetryPolicy(max_retries=3, delay=30))
def flaky_asset():
    ...

# Job-level max concurrency
job = dg.define_asset_job(
    "my_job",
    selection=dg.AssetSelection.all(),
    config={"execution": {"config": {"multiprocess": {"max_concurrent": 4}}}},
)

# Tag runs for UI filtering
return dg.RunRequest(tags={"team": "data-eng", "env": "prod"})
```

---

## Decision Tables

### When to use Resource vs. IO Manager

| Need | Use |
|------|-----|
| Talk to an external system *inside* asset logic | **Resource** (`ConfigurableResource`) |
| Control how asset *outputs are persisted* between assets | **IO Manager** |
| Database client for querying data | **Resource** |
| Write all assets to S3 Parquet automatically | **IO Manager** |
| Send a Slack notification | **Resource** |
| Swap storage from local disk to cloud | **IO Manager** |

### When to use Schedule vs. Sensor

| Need | Use |
|------|-----|
| Run on a fixed time interval | **Schedule** (`ScheduleDefinition`) |
| Run when a file arrives / API changes | **Sensor** (`@sensor`) |
| Run when an upstream asset materialises | **Asset Sensor** (`@asset_sensor`) |
| Run the latest partition daily | **`build_schedule_from_partitioned_job`** |
| React to a message queue or webhook | **Sensor** with cursor |

### Partition type selection

| Data shape | Use |
|------------|-----|
| Time-series, processed incrementally | `DailyPartitionsDefinition` (or Hourly/Weekly/Monthly) |
| Fixed categories (regions, environments) | `StaticPartitionsDefinition` |
| Categories discovered at runtime | `DynamicPartitionsDefinition` |
| Two independent axes (date × region) | `MultiPartitionsDefinition` |

---

## Common Gotchas

| Symptom | Likely cause |
|---------|--------------|
| Asset not visible in the UI | Not registered in `Definitions(assets=[...])` |
| Schedule not firing | Schedule is toggled **off** — enable in Automation → Schedules |
| Sensor not triggering | Sensor is toggled **off** — enable in Automation → Sensors |
| `KeyError` on resource injection | Parameter name in asset ≠ key in `Definitions(resources={...})` |
| Downstream asset receives `None` | Upstream `@asset` returns `None` (implicit or explicit) |
| `EnvVar` value not resolved | Env var not set in the shell running `dg dev` |
| Backfill creates 1 run, not N | `partitions_def` missing from the `define_asset_job` call |
| Re-materializing same file twice via sensor | `run_key` not set on `RunRequest` — set it to a unique file identifier |
| Import error on `dg dev` reload | Syntax error in a `defs/` file — check the error banner in the UI |
| Sensor cursor resets after restart | `context.update_cursor(...)` not called at end of sensor evaluation |
