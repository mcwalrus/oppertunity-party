# Unit 09 — Production Patterns

## What you will learn

- How IO Managers decouple asset logic from storage and enable plug-and-play backends
- How to attach rich metadata and lineage information to materializations
- Multi-code-location deployments: isolating domains with independent environments
- Deployment options: self-hosted OSS vs. Dagster+ (cloud)
- Key operational patterns: retries, concurrency, tagging, and run monitoring

## Why this unit exists

Units 01–08 give you correct Dagster code. This unit bridges correct code to
*production-grade* deployments. The patterns here — IO managers, multi-code
locations, run retries, observability — are what separate a prototype that works
in `dg dev` from a pipeline that runs unattended and recovers from failures.

---

## 1. IO Managers: separating storage from logic

An **IO Manager** controls *how the return value of an asset is persisted* and
*how upstream return values are loaded* as inputs. By default, Dagster uses an
in-memory IO manager (output is a Python object in RAM). In production you want
a durable backend.

```python
import dagster as dg

# Built-in: persist each output as a pickle file on the local filesystem
defs = dg.Definitions(
    assets=[...],
    resources={"io_manager": dg.fs_io_manager},
)
```

**S3 + Parquet (using dagster-aws):**

```bash
pip install dagster-aws
```

```python
from dagster_aws.s3 import S3PickleIOManager, S3Resource

defs = dg.Definitions(
    assets=[...],
    resources={
        "io_manager": S3PickleIOManager(
            s3_resource=S3Resource(),
            s3_bucket=dg.EnvVar("S3_BUCKET"),
            s3_prefix="dagster-io",
        ),
    },
)
```

Every asset output is now written to S3 automatically — **without changing a
single line of asset code**. This is the power of IO Manager abstraction.

**Custom IO Manager (e.g., DataFrame → Snowflake table):**

```python
from dagster import IOManager, OutputContext, InputContext
import pandas as pd

class SnowflakeDataFrameIOManager(IOManager):
    def handle_output(self, context: OutputContext, obj: pd.DataFrame):
        table = context.asset_key.path[-1]
        obj.to_sql(table, con=snowflake_engine, if_exists="replace")
        context.add_output_metadata({"rows": len(obj)})

    def load_input(self, context: InputContext) -> pd.DataFrame:
        table = context.asset_key.path[-1]
        return pd.read_sql(f"SELECT * FROM {table}", con=snowflake_engine)
```

> **Where the IO Manager analogy breaks down vs. Resources:** A Resource is
> something your asset code *calls*. An IO Manager is something that *wraps*
> your asset — you never call it explicitly; Dagster calls it for you before and
> after every asset execution.

---

## 2. Rich metadata and data lineage

Materializations can carry metadata that makes the asset graph a living
data catalog:

```python
import dagster as dg
import pandas as pd

@dg.asset
def orders(context: dg.AssetExecutionContext) -> pd.DataFrame:
    df = pd.read_parquet("s3://my-bucket/orders.parquet")

    context.add_output_metadata({
        "row_count":     dg.MetadataValue.int(len(df)),
        "schema":        dg.MetadataValue.json(dict(df.dtypes.astype(str))),
        "sample":        dg.MetadataValue.md(df.head(5).to_markdown()),
        "s3_path":       dg.MetadataValue.url("s3://my-bucket/orders.parquet"),
        "dagster/column_schema": dg.TableSchema(
            columns=[dg.TableColumn(name=c, type=str(t)) for c, t in df.dtypes.items()]
        ),
    })
    return df
```

`dagster/column_schema` is a special metadata key — Dagster renders the schema
in the UI's **Catalog** view and tracks schema evolution across materializations.

---

## 3. Multi-code-location deployments

As teams grow, different domains (ingestion, ML, reporting) need isolated Python
environments and independent deploy cycles. Each domain becomes its own **code
location** with its own `Definitions` object:

```
workspace.yaml
├── ingestion_team/        → Python env with pandas, boto3, requests
│   └── definitions.py
├── ml_team/               → Python env with torch, scikit-learn
│   └── definitions.py
└── reporting_team/        → Python env with plotly, jinja2
    └── definitions.py
```

```yaml
# workspace.yaml
load_from:
  - python_module: ingestion_team.definitions
  - python_module: ml_team.definitions
  - python_module: reporting_team.definitions
```

All three code locations appear in **one** Dagster UI with a unified asset
graph and end-to-end lineage — but run in separate processes with separate
dependencies.

---

## 4. Deployment options

| Option | Best for | Setup |
|--------|----------|-------|
| **OSS self-hosted** | Full control, on-prem, cost-sensitive | `dagster-webserver` + `dagster-daemon` + PostgreSQL backend + your own infra |
| **Dagster+** | Teams that want managed infra | Serverless or hybrid agent; no server management |
| **Docker Compose** | Single-machine or CI | `docker-compose up` with official images |
| **Kubernetes** | Production scale, multi-team | Helm chart + user code deployments |

For a new team: **start with OSS on a single VM or Dagster+** — the operational
overhead of Kubernetes is not worth it until you have multiple code locations or
heavy concurrent runs.

> Grounded in: [Dagster deployment documentation](https://docs.dagster.io/deployment)

---

## 5. Retries, concurrency, and run configuration

**Asset-level retries:**

```python
@dg.asset(
    retry_policy=dg.RetryPolicy(max_retries=3, delay=30),  # 3 retries, 30s delay
)
def flaky_api_asset():
    return call_unreliable_api()
```

**Job-level concurrency:**

```python
ingestion_job = dg.define_asset_job(
    name="ingestion_job",
    selection=dg.AssetSelection.groups("ingestion"),
    config={
        "execution": {
            "config": {"multiprocess": {"max_concurrent": 4}}
        }
    },
)
```

**Run tags for filtering in the UI:**

```python
@dg.schedule(job=ingestion_job, cron_schedule="0 6 * * *")
def daily_schedule(context):
    return dg.RunRequest(
        tags={"team": "data-eng", "env": "prod"},
    )
```

Tags appear in the Runs page and can be filtered on.

---

## 6. Observability checklist for production

| Practice | How |
|----------|-----|
| Attach row counts to every asset | `context.add_output_metadata({"row_count": N})` |
| Use asset checks for data quality gates | `@asset_check` with `ERROR` severity |
| Tag runs by environment and team | `RunRequest(tags={"env": "prod"})` |
| Set retry policies on flaky assets | `@dg.asset(retry_policy=RetryPolicy(...))` |
| Use `dg.EnvVar` for all secrets | Never hardcode credentials |
| Partition large historical assets | Avoid full-table scans on every run |
| Pin your Dagster version in `pyproject.toml` | Avoid surprise upgrades in prod |

---

## Practical Exercises

1. **Swap IO managers.** Add `dg.fs_io_manager` to your dev `Definitions`.
   Materialize an asset. Find the pickled output on disk in `$DAGSTER_HOME`.
   Write a second asset that depends on it — confirm it loads the persisted
   value, not a re-computed one.

2. **Rich metadata.** Add `row_count`, `schema`, and a `sample` to one of your
   DataFrame assets. Check the Catalog view in the UI — confirm the metadata is
   displayed per materialization.

3. **Retry policy.** Write an asset that fails 2 out of 3 times (use
   `random.random()` to simulate). Attach `RetryPolicy(max_retries=3)`. Run it
   and watch the retry attempts in the run log.

4. **Multi-code-location.** Create a second minimal project directory with its
   own `definitions.py` and one `@asset`. Create a `workspace.yaml` at the
   project root pointing at both. Run `dagster dev -w workspace.yaml` and
   confirm both code locations' assets appear in one UI.

---

## Self-Check

1. You change your IO Manager from `fs_io_manager` to `S3PickleIOManager`.
   Do you need to modify any asset code? Why or why not?

2. Two code locations both define an asset named `orders`. What happens in the
   Dagster UI?

3. An asset with `RetryPolicy(max_retries=2)` fails on the first attempt due to
   a `ValueError` in your business logic (not a transient network error). How
   many total attempts will Dagster make?

---

## Key Takeaways

- IO Managers decouple asset logic from storage — swap backends (disk → S3 →
  Snowflake) without touching asset code.
- Attach `row_count`, `schema`, and sample metadata to every materialization —
  this turns the asset graph into a living data catalog.
- Multi-code-location deployments isolate team environments while sharing one
  UI and one asset lineage graph.
- Retries, concurrency, and run tags are job/asset-level configuration — no
  infrastructure changes needed.
- For new deployments: start with OSS single-VM or Dagster+; add Kubernetes
  only when multi-team concurrency demands it.

---

*You've completed the course. Keep the [CHEATSHEET](../../CHEATSHEET.md) handy
as your day-to-day reference.*
