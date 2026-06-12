# Unit 08 — Testing & Asset Checks

## What you will learn

- How to unit test assets by calling them as plain Python functions
- How to mock resources in tests using direct instantiation or subclassing
- How to test assets with upstream dependencies using `input_values`
- How to test partitioned assets with `build_asset_context`
- How to write `@asset_check` for in-pipeline data quality validation

## Why this unit exists

Data pipelines that aren't tested are configuration. An untested ETL that
silently returns the wrong row counts, wrong joins, or wrong data types causes
downstream decisions to be made on bad data — often discovered weeks later.
Dagster makes assets testable by design: they are plain Python functions.
This unit shows how to exploit that property systematically.

---

## 1. The core insight: assets are just functions

Unlike Airflow operators (which require a DAG, a task context, and an executor
to run), Dagster assets are decorated Python functions. You call them directly
in tests:

```python
# defs/assets.py
import dagster as dg

@dg.asset
def cleaned_orders(raw_orders):
    return [o for o in raw_orders if o["amount"] > 0]
```

```python
# tests/test_assets.py
from my_project.defs.assets import cleaned_orders

def test_cleaned_orders_filters_negative():
    result = cleaned_orders(raw_orders=[
        {"id": 1, "amount": 100},
        {"id": 2, "amount": -5},   # should be filtered out
        {"id": 3, "amount": 0},    # should be filtered out
    ])
    assert result == [{"id": 1, "amount": 100}]
    # → passes: negative and zero-amount orders are removed
```

No fixtures, no mocking framework, no Dagster machinery. Just a function call.

---

## 2. Testing assets with resources

Pass resource instances directly as arguments:

```python
# defs/assets.py
import dagster as dg

class DatabaseResource(dg.ConfigurableResource):
    connection_string: str
    def fetch_users(self): ...

@dg.asset
def active_users(database: DatabaseResource):
    return [u for u in database.fetch_users() if u["active"]]
```

```python
# tests/test_assets.py
from my_project.defs.assets import active_users
from my_project.defs.resources import DatabaseResource

class FakeDatabase(DatabaseResource):
    def fetch_users(self):
        return [
            {"id": 1, "active": True},
            {"id": 2, "active": False},
        ]

def test_active_users_filters_inactive():
    result = active_users(database=FakeDatabase(connection_string="fake://"))
    assert len(result) == 1
    assert result[0]["id"] == 1
    # → passes: only active user returned
```

> **Grounded in:** [docs.dagster.io/guides/test/unit-testing-assets-and-ops](https://docs.dagster.io/guides/test/unit-testing-assets-and-ops)

---

## 3. Testing assets with context using `build_asset_context`

When an asset uses `context` (for `partition_key`, `log`, or metadata), build a
test context with `dg.build_asset_context`:

```python
# defs/assets.py
@dg.asset(partitions_def=dg.DailyPartitionsDefinition(start_date="2024-01-01"))
def daily_report(context: dg.AssetExecutionContext):
    date = context.partition_key
    return f"Report for {date}"
```

```python
# tests/test_assets.py
import dagster as dg
from my_project.defs.assets import daily_report

def test_daily_report_includes_date():
    context = dg.build_asset_context(partition_key="2024-03-15")
    result = daily_report(context=context)
    assert "2024-03-15" in result
    # → passes: report contains the expected date
```

---

## 4. Testing multi-assets and assets with `input_values`

`build_asset_context` accepts `input_values` for assets that receive upstream
values but you don't want to run the full upstream chain:

```python
# defs/assets.py
@dg.asset
def enriched_orders(cleaned_orders, customers):
    return [{**o, "customer_name": customers.get(o["customer_id"])} for o in cleaned_orders]
```

```python
# tests/test_assets.py
import dagster as dg
from my_project.defs.assets import enriched_orders

def test_enrichment_joins_customer_name():
    ctx = dg.build_asset_context(
        input_values={
            "cleaned_orders": [{"id": 1, "customer_id": 42}],
            "customers": {42: "Alice"},
        }
    )
    result = enriched_orders(ctx)
    assert result[0]["customer_name"] == "Alice"
```

> **Note:** `input_values` works for assets decorated with `@asset`. For
> `@multi_asset` with upstream assets, use a mock IO manager instead — see
> the [Dagster testing docs](https://docs.dagster.io/guides/test/unit-testing-assets-and-ops#multi-assets-upstream).

---

## 5. `@asset_check` — in-pipeline data quality

`@asset_check` runs after an asset materializes and validates its output. Checks
are visible in the UI alongside the asset they guard:

```python
import dagster as dg

@dg.asset
def orders():
    return [{"id": 1, "amount": 100}, {"id": 2, "amount": 150}]

@dg.asset_check(asset=orders)
def orders_not_empty(orders) -> dg.AssetCheckResult:
    return dg.AssetCheckResult(
        passed=len(orders) > 0,
        metadata={"row_count": len(orders)},
    )
    # → UI shows a green check badge on the orders asset if passed

@dg.asset_check(asset=orders)
def no_negative_amounts(orders) -> dg.AssetCheckResult:
    negatives = [o for o in orders if o["amount"] < 0]
    return dg.AssetCheckResult(
        passed=len(negatives) == 0,
        severity=dg.AssetCheckSeverity.WARN if negatives else dg.AssetCheckSeverity.ERROR,
        metadata={"negative_count": len(negatives)},
    )
```

Register checks in `Definitions`:

```python
defs = dg.Definitions(
    assets=[orders],
    asset_checks=[orders_not_empty, no_negative_amounts],
)
```

**Severity levels:**

| Severity | Behaviour |
|----------|-----------|
| `ERROR` (default) | Failed check marks the asset as failed; downstream blocked |
| `WARN` | Failed check shows warning badge; downstream proceeds |

---

## 6. Unit testing asset checks

Asset checks are also plain Python functions — call them directly:

```python
from my_project.defs.checks import orders_not_empty, no_negative_amounts

def test_orders_not_empty_passes():
    result = orders_not_empty(orders=[{"id": 1, "amount": 100}])
    assert result.passed

def test_orders_not_empty_fails_on_empty():
    result = orders_not_empty(orders=[])
    assert not result.passed

def test_no_negative_amounts_warns():
    result = no_negative_amounts(orders=[{"id": 1, "amount": -50}])
    assert not result.passed
```

---

## Practical Exercises

1. **Basic unit test.** Write `cleaned_orders` and two tests: one that passes
   valid orders and asserts they're returned unchanged, one that passes orders
   with negative amounts and asserts they're filtered out.

2. **Resource test.** Write an asset that uses a `DatabaseResource`. Create a
   `FakeDatabase` subclass returning a fixed list. Test the asset with the fake.

3. **Partitioned asset test.** Write a partitioned asset that uses
   `context.partition_key` in its return value. Use `build_asset_context` with
   a specific `partition_key`. Assert the output reflects that key.

4. **Asset check.** Add `orders_not_empty` and `no_negative_amounts` checks to
   your `orders` asset. Register them in `Definitions`. Materialize from the UI
   and observe the check results in the asset's "Checks" tab. Then write unit
   tests for both checks.

---

## Self-Check

1. Why can you call a Dagster `@asset` function directly in a test without
   spinning up a Dagster instance?

2. When would you use `input_values` in `build_asset_context` vs. simply
   passing upstream values as function arguments?

3. You have an `@asset_check` with `severity=WARN` that fails. Does the
   downstream asset still materialize?

---

## Key Takeaways

- Assets are plain Python functions — call them directly in tests. No Dagster
  machinery required.
- Resources are injected via the function signature — swap in a test double by
  passing a fake instance directly.
- `dg.build_asset_context(partition_key=..., input_values=...)` provides a
  test context for assets that use `context`.
- `@asset_check` enforces data quality in-pipeline; checks run after
  materialization and are visible in the UI.
- Asset checks are also plain functions — unit-test them the same way you test
  assets.

## Next

[Unit 09 — Production Patterns](../09-production-patterns/README.md)
