# Unit 02 — Software-Defined Assets

## What you will learn

- How to define an asset with the `@asset` decorator
- How to express upstream dependencies using function arguments
- How Dagster determines execution order from the dependency graph
- How to attach metadata to a materialization
- How `@multi_asset` produces multiple outputs from one function

## Why this unit exists

Assets are the primary abstraction in Dagster. Every other concept — resources,
partitions, sensors, jobs — exists to serve assets. Getting the `@asset` pattern
solid before moving on prevents a class of confusion where people try to bolt
other concepts onto a shaky foundation.

---

## 1. The `@asset` decorator

The simplest possible asset is a function that returns a value:

```python
import dagster as dg

@dg.asset
def raw_temperature():
    # Fetches data; in real life, call an API or read a file
    return [22.1, 19.4, 23.7, 18.9]
    # → stored by Dagster's default IO manager (in-memory during dev)
```

The function name (`raw_temperature`) becomes the **asset key** — the identifier
Dagster uses in the UI and dependency graph. The return value is the
*materialization output*: whatever your IO manager saves to storage.

> **Surprises everyone coming from Airflow:** There is no explicit `return`
> required in an Airflow task — tasks are usually fire-and-forget side effects.
> In Dagster, `return` is how you hand data to downstream assets. Returning
> `None` is valid but means downstream assets get `None` as input.

---

## 2. Expressing dependencies with function arguments

To declare that asset B depends on asset A, list A as a parameter of B's
function. Dagster infers the dependency from the argument name:

```python
import dagster as dg

@dg.asset
def raw_temperature():
    return [22.1, 19.4, 23.7, 18.9]

@dg.asset
def cleaned_temperature(raw_temperature):           # ← argument name = upstream asset key
    return [t for t in raw_temperature if t > 0]   # receives the return value of raw_temperature
    # → [22.1, 19.4, 23.7, 18.9]  (all positive, so unchanged)

@dg.asset
def average_temperature(cleaned_temperature):
    return sum(cleaned_temperature) / len(cleaned_temperature)
    # → 21.025
```

Dagster builds the execution order automatically: `raw_temperature` →
`cleaned_temperature` → `average_temperature`. You never call these functions
yourself — Dagster calls them and passes the outputs as inputs.

> **Where the analogy breaks down vs. function calls:** In Python you'd just
> call `cleaned_temperature(raw_temperature())`. In Dagster, the output of
> `raw_temperature` is *serialized to storage* (by the IO manager) before being
> passed as input to `cleaned_temperature`. This is what enables restarting a
> failed pipeline mid-way — the intermediate outputs already exist.

---

## 3. Asset keys, groups, and prefixes

By default the asset key is the function name. You can override it or add a
namespace with `key_prefix`:

```python
@dg.asset(key_prefix=["warehouse", "metrics"])
def daily_active_users():
    return 42
    # → asset key is warehouse/metrics/daily_active_users
```

Assets with the same `group_name` are visually grouped in the UI:

```python
@dg.asset(group_name="ingestion")
def raw_orders():
    ...

@dg.asset(group_name="ingestion")
def raw_customers():
    ...

@dg.asset(group_name="transformed", deps=["raw_orders", "raw_customers"])
def orders_with_customers():
    ...
```

---

## 4. Attaching metadata to a materialization

Assets can emit metadata alongside their output — row counts, schemas, preview
rows. This metadata appears in the UI on every materialization event:

```python
import dagster as dg

@dg.asset
def orders(context: dg.AssetExecutionContext):
    data = [{"id": 1, "amount": 99.0}, {"id": 2, "amount": 149.0}]

    context.add_output_metadata({
        "row_count": len(data),
        "preview": dg.MetadataValue.json(data[:3]),
    })
    return data
    # → UI shows: row_count=2, preview=[...]
```

`context` is the execution context — an optional first argument that gives you
access to logging, metadata, partition keys, and run information.

---

## 5. `@multi_asset` — one function, multiple outputs

When a single computation produces multiple logically distinct datasets, use
`@multi_asset`:

```python
import dagster as dg

@dg.multi_asset(
    specs=[
        dg.AssetSpec("users"),
        dg.AssetSpec("sessions"),
    ]
)
def fetch_analytics():
    users = [{"id": 1}, {"id": 2}]
    sessions = [{"user_id": 1, "duration": 120}]
    return users, sessions
    # → both assets are materialized in one run
```

Use `@multi_asset` when splitting the computation would be artificial or
expensive (e.g., a single API call that returns two related tables).

---

## 6. `deps` — declaring dependencies without receiving the value

Sometimes you need to express "B depends on A" but B doesn't actually read A's
output (it reads from an external system that A populated):

```python
@dg.asset
def load_to_warehouse():
    # writes to Snowflake; doesn't return the data
    ...

@dg.asset(deps=["load_to_warehouse"])
def downstream_report():
    # reads directly from Snowflake, doesn't need the Python object
    ...
```

`deps` declares the ordering dependency without requiring Dagster to pass the
upstream return value as a Python argument.

---

## Practical Exercises

1. **Three-asset chain.** Create a file `defs/temperature.py` with the
   `raw_temperature → cleaned_temperature → average_temperature` chain from
   §2. Add it to your `Definitions` (see Unit 03 for the pattern, or import and
   list it manually). Open the UI and verify the three assets appear with arrows.
   Materialize all three and inspect each one's "Latest Materialization" tab.

2. **Add metadata.** Modify `cleaned_temperature` to accept a `context`
   argument and emit `row_count` as output metadata. Re-materialize and confirm
   the metadata appears in the UI.

3. **Multi-asset.** Write a `@multi_asset` that returns a `users` list and a
   `sessions` list. Confirm both appear as separate nodes in the asset graph.

4. **Deps without value.** Write an asset `db_seed` that prints "seeding…" and
   returns `None`. Write a second asset `summary` with `deps=["db_seed"]` that
   prints "summarising…". Materialize both and verify the order of execution in
   the run log.

---

## Self-Check

1. How does Dagster know that `cleaned_temperature` should run after
   `raw_temperature`? What is the mechanism?

2. What is the difference between declaring a dependency via a function argument
   vs. using `deps=[...]`?

3. You want to attach the row count of a DataFrame to the materialization event
   so it shows in the UI. What Dagster API do you use?

---

## Key Takeaways

- `@asset` turns a Python function into a declared data asset. The return value
  is the materialization output.
- Upstream dependencies are expressed as function arguments — argument name
  matches asset key.
- Dagster builds execution order automatically from the dependency graph; you
  never wire tasks manually.
- `context.add_output_metadata()` attaches observable data (row counts, schemas)
  to each materialization event.
- `@multi_asset` handles one computation → multiple assets; `deps=[...]`
  handles ordering without value passing.

## Next

[Unit 03 — The Definitions Object & Project Structure](../03-definitions-and-structure/README.md)
