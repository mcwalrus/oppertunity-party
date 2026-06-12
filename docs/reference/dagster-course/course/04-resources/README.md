# Unit 04 — Resources: Managed External Connections

## What you will learn

- What a Dagster resource is and why injection beats direct imports
- How to define a `ConfigurableResource` with typed, validated config
- How to inject resources into assets and reference them via `context`
- How to supply different resource implementations per environment
- The difference between a Resource and an IO Manager (when to use each)

## Why this unit exists

Without resources, assets import database connections or API clients directly —
hardcoding credentials, making tests require real infrastructure, and scattering
config across files. Resources centralise external connections, make them
testable, and make per-environment configuration explicit. This unit unlocks
clean, testable asset code.

---

## 1. Why resources exist

Compare these two approaches:

```python
# ❌ Without resources — coupled, hard to test
import psycopg2

@dg.asset
def orders():
    conn = psycopg2.connect("postgresql://prod-host/mydb")   # hardcoded
    return conn.execute("SELECT * FROM orders").fetchall()
```

```python
# ✅ With resources — injectable, testable
import dagster as dg

class DatabaseResource(dg.ConfigurableResource):
    connection_string: str

    def fetch_orders(self):
        import psycopg2
        conn = psycopg2.connect(self.connection_string)
        return conn.execute("SELECT * FROM orders").fetchall()

@dg.asset
def orders(database: DatabaseResource):
    return database.fetch_orders()
    # → same asset code works against dev DB, prod DB, or a mock
```

The `orders` asset no longer knows *which* database it connects to. That
decision lives in `Definitions`, making it trivially swappable per environment.

---

## 2. Defining a `ConfigurableResource`

`ConfigurableResource` is a Pydantic model that also registers itself with
Dagster. Fields are declared as class attributes with type annotations:

```python
import dagster as dg
from pydantic import Field

class SlackNotifier(dg.ConfigurableResource):
    webhook_url: str
    channel: str = Field(default="#data-alerts")  # optional with default

    def send(self, message: str) -> None:
        import requests
        requests.post(self.webhook_url, json={"channel": self.channel, "text": message})
```

Dagster validates config at startup using Pydantic — type errors surface before
any asset runs, not mid-pipeline.

> **Analogy to dependency injection frameworks:** `ConfigurableResource` is
> essentially a typed service in a DI container. You declare what you need;
> Dagster wires it in. The difference from frameworks like FastAPI's `Depends`:
> resources are resolved once per run, not per call.

---

## 3. Injecting resources into assets

Declare a resource as a parameter whose type annotation is the resource class:

```python
@dg.asset
def send_report(slack: SlackNotifier):
    slack.send("Daily report complete ✓")
    # → sends a Slack message using whatever SlackNotifier was wired in
```

Register the resource in `Definitions`:

```python
defs = dg.Definitions(
    assets=[send_report],
    resources={
        "slack": SlackNotifier(
            webhook_url="https://hooks.slack.com/services/...",
            channel="#data-alerts",
        ),
    },
)
```

The key in `resources={}` (`"slack"`) must match the parameter name in the
asset function (`slack: SlackNotifier`).

---

## 4. Per-environment configuration

Use environment variables to avoid hardcoding secrets. `ConfigurableResource`
reads them automatically when you use `EnvVar`:

```python
import dagster as dg

class WarehouseResource(dg.ConfigurableResource):
    host: str
    password: str

defs = dg.Definitions(
    assets=[...],
    resources={
        "warehouse": WarehouseResource(
            host=dg.EnvVar("WAREHOUSE_HOST"),
            password=dg.EnvVar("WAREHOUSE_PASSWORD"),
        ),
    },
)
```

`EnvVar("X")` is resolved at runtime, not import time — safe to commit.

**Pattern: one `Definitions` per environment via a factory:**

```python
# definitions.py
import os, dagster as dg
from my_project.defs import all_assets

def make_defs(env: str) -> dg.Definitions:
    if env == "prod":
        db = WarehouseResource(host=dg.EnvVar("PROD_HOST"), password=dg.EnvVar("PROD_PASS"))
    else:
        db = WarehouseResource(host="localhost", password="dev")
    return dg.Definitions(assets=all_assets, resources={"warehouse": db})

defs = make_defs(os.getenv("DAGSTER_ENV", "dev"))
```

---

## 5. Resources vs. IO Managers — when to use each

This is the most common source of confusion for new Dagster users.

| Question | Resource | IO Manager |
|----------|----------|------------|
| "I need a DB connection to query data inside an asset" | ✅ Resource | ❌ |
| "I want to control *how asset outputs are stored/loaded* between assets" | ❌ | ✅ IO Manager |
| "I'm calling an API and returning data" | ✅ Resource | ❌ |
| "I want all my assets to persist to S3 as Parquet by default" | ❌ | ✅ IO Manager |

> Rule of thumb from [Dagster docs discussion #15523](https://github.com/dagster-io/dagster/discussions/15523):
> **Use a Resource when you need to talk to an external system inside your asset
> logic. Use an IO Manager when you want to change how the output of an asset is
> persisted between assets.**

IO Managers are covered in Unit 09.

---

## 6. Resources in tests

Swap the real resource for a test double by instantiating with test config:

```python
# tests/test_assets.py
from my_project.defs.assets import send_report
from my_project.defs.resources import SlackNotifier

def test_send_report(capsys):
    # No real Slack call — use a test webhook URL or a mock subclass
    class FakeSlack(SlackNotifier):
        messages: list = []
        def send(self, message: str):
            self.messages.append(message)

    result = send_report(slack=FakeSlack(webhook_url="fake", channel="#test"))
    # Direct invocation — Dagster assets are just Python functions
    assert result is None  # send_report returns nothing, side effect verified
```

Because assets are plain Python functions, you call them directly in tests —
no Dagster machinery needed. This is the whole payoff of injection.

---

## Practical Exercises

1. **Define a resource.** Create a `WeatherApiResource(ConfigurableResource)`
   with an `api_key: str` field and a `get_temperature(city: str) -> float`
   method that returns a hardcoded value (simulate the API). Wire it into a
   `daily_temperature` asset.

2. **Environment variables.** Replace the hardcoded `api_key` with
   `dg.EnvVar("WEATHER_API_KEY")`. Set the env var in your shell and confirm
   the resource initialises correctly. Confirm it fails (with a clear error)
   when the env var is missing.

3. **Multiple resources.** Add a second resource (e.g., `SlackNotifier`) to
   the same asset. Register both in `Definitions`. Confirm both appear in the
   Dagster UI's "Resources" tab.

4. **Test without real infra.** Write a unit test for `daily_temperature` that
   passes a fake `WeatherApiResource` returning `21.5`. Assert the asset
   returns that value. Run with `pytest` — it should pass with no network call.

---

## Self-Check

1. You wire a resource with key `"db"` in `Definitions(resources={"db": ...})`
   but your asset parameter is named `database`. What happens when you
   materialize, and how do you fix it?

2. What does `dg.EnvVar("X")` do that `os.environ["X"]` does not?

3. You want every asset's output to be written to S3 as a Parquet file
   automatically. Should you use a Resource or an IO Manager?

---

## Key Takeaways

- `ConfigurableResource` is a typed, validated service object — declared once,
  injected everywhere.
- The parameter name in an asset function must match the key in
  `Definitions(resources={...})`.
- `dg.EnvVar("X")` resolves at runtime, not import time — safe to commit.
- Testing with resources is direct Python function invocation — pass a test
  double as the argument.
- Resources handle "talk to external systems inside assets"; IO Managers handle
  "how outputs are stored between assets". They are not interchangeable.

## Next

[Unit 05 — Jobs & Schedules](../05-jobs-and-schedules/README.md)
