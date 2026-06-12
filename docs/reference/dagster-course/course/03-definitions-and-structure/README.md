# Unit 03 — The Definitions Object & Project Structure

## What you will learn

- What `Definitions` is and why everything must be registered in it
- How to load assets automatically with `load_assets_from_modules`
- How code locations isolate independently deployable units
- The recommended project layout that scales beyond the starter template
- How to use `dg scaffold` to generate boilerplate

## Why this unit exists

`Definitions` is the single most important wiring concept in Dagster. It is the
boundary between your Python code and the Dagster runtime. Without understanding
it you can't reason about what Dagster sees, why an asset isn't showing up in
the UI, or how to structure a project that grows beyond a handful of files.

---

## 1. `Definitions` — the deployment contract

`Definitions` is a Python object you construct at module load time. It accepts
lists of assets, resources, schedules, sensors, jobs, and IO managers. The
Dagster webserver loads this object; anything not listed here does not exist
in the Dagster UI or daemon.

```python
# src/my_project/definitions.py
import dagster as dg

from my_project.defs.assets import raw_orders, cleaned_orders, order_report

defs = dg.Definitions(
    assets=[raw_orders, cleaned_orders, order_report],
)
```

The entry point is declared in `pyproject.toml` (scaffolded automatically):

```toml
# pyproject.toml
[tool.dagster]
module_name = "my_project.definitions"
```

> **Surprises everyone coming from Airflow:** In Airflow you drop `.py` files
> into a `dags/` folder and the scheduler picks them up automatically. In
> Dagster you explicitly register every asset, schedule, and sensor in
> `Definitions`. This feels verbose at first but is the source of a key
> guarantee: **there are no surprises in production**. What's in `Definitions`
> is exactly what runs.

---

## 2. Loading assets from modules automatically

Listing every asset individually doesn't scale. Use
`load_assets_from_modules` or `load_assets_from_package_module` to collect
all `@asset`-decorated functions from a module:

```python
# src/my_project/definitions.py
import dagster as dg
from my_project import defs as defs_module

# Automatically picks up every @asset in the defs package
all_assets = dg.load_assets_from_package_module(defs_module)

defs = dg.Definitions(assets=all_assets)
```

Or, using the newer `dg.Definitions.merge` pattern — combine definitions
from sub-packages:

```python
import dagster as dg
from my_project.defs import ingestion, transforms, reporting

defs = dg.Definitions.merge(
    ingestion.defs,
    transforms.defs,
    reporting.defs,
)
```

Each sub-package exposes its own `defs = dg.Definitions(...)` — this keeps each
domain independently testable and readable.

---

## 3. Recommended project structure

> Grounded in: [docs.dagster.io — Organizing your Dagster project](https://docs.dagster.io/guides/build/projects/project-structure/organizing-dagster-projects)

```
my-project/
├── pyproject.toml              # entry point + dependencies
├── uv.lock
└── src/
    └── my_project/
        ├── __init__.py
        ├── definitions.py      # top-level Definitions — the only thing Dagster loads
        └── defs/
            ├── __init__.py
            ├── ingestion/
            │   ├── __init__.py
            │   ├── assets.py   # @asset-decorated functions
            │   └── resources.py
            ├── transforms/
            │   ├── __init__.py
            │   └── assets.py
            └── reporting/
                ├── __init__.py
                └── assets.py
tests/
├── __init__.py
└── test_assets.py
```

**Rule of thumb:** one directory per domain or data source. Each directory owns
its assets, resources, and any local utilities. `definitions.py` assembles them.

---

## 4. Code locations

A **code location** is a Python environment that contains exactly one
`Definitions` object. Most projects start with one code location — the entire
project is one environment.

As projects grow, teams split into multiple code locations so that different
domains can have different Python dependencies and be deployed independently:

```yaml
# workspace.yaml (used in multi-code-location setups)
load_from:
  - python_module: ingestion_team.definitions
  - python_module: ml_team.definitions
```

With multiple code locations, each team's assets still appear in the **same**
Dagster UI and asset graph. The UI merges them; the execution environments stay
separate.

> **Analogy:** Code locations are like microservices — independently deployable,
> separately versioned, but unified behind one API gateway (the Dagster UI).

---

## 5. Scaffolding with `dg scaffold`

The `dg` CLI generates boilerplate so you don't hand-write repetitive files:

```bash
# Create a new asset file
dg scaffold defs dagster.asset src/my_project/defs/ingestion/raw_events.py
# → generates raw_events.py with @dg.asset stub + Definitions object

# Create a schedule
dg scaffold defs dagster.schedule src/my_project/defs/schedules.py

# Create a sensor
dg scaffold defs dagster.sensor src/my_project/defs/sensors.py
```

Scaffolded files include the correct imports and a minimal working skeleton.

---

## 6. A minimal working `definitions.py`

Here is the smallest `definitions.py` that registers assets from a sub-package:

```python
# src/my_project/definitions.py
import dagster as dg
from my_project.defs.ingestion import assets as ingestion_assets
from my_project.defs.transforms import assets as transform_assets

defs = dg.Definitions(
    assets=dg.load_assets_from_modules([ingestion_assets, transform_assets]),
)
```

And the corresponding asset files stay clean — just `@asset` functions:

```python
# src/my_project/defs/ingestion/assets.py
import dagster as dg

@dg.asset(group_name="ingestion")
def raw_events():
    return {"events": [1, 2, 3]}

@dg.asset(group_name="ingestion")
def raw_users():
    return [{"id": 1, "name": "Alice"}]
```

---

## Practical Exercises

1. **Manual registration.** Write two assets in a single file. Register them
   explicitly in `Definitions(assets=[...])`. Confirm both appear in the UI.
   Then add a third asset to the file without registering it — confirm it does
   NOT appear in the UI.

2. **Module loading.** Refactor to use `load_assets_from_modules`. Add the
   previously missing asset to the module — confirm it now appears automatically.

3. **Sub-package split.** Create `defs/ingestion/assets.py` and
   `defs/transforms/assets.py`, each with one or two assets. Use
   `load_assets_from_modules` on both in `definitions.py`. Confirm the
   group-level visual separation in the UI.

4. **Scaffold an asset.** Run
   `dg scaffold defs dagster.asset src/my_project/defs/new_asset.py` and
   inspect the generated file. What does it give you that a blank file doesn't?

---

## Self-Check

1. A colleague adds a new `@asset` function to `defs/reporting/assets.py` but
   it doesn't appear in the Dagster UI. What is the most likely cause?

2. What is the difference between a *code location* and a *project*? Can you
   have multiple code locations in one project?

3. What does `load_assets_from_package_module` do that listing assets manually
   doesn't?

---

## Key Takeaways

- `Definitions` is the deployment contract — everything not in it is invisible
  to Dagster.
- `load_assets_from_modules` / `load_assets_from_package_module` auto-collects
  `@asset` functions so you don't enumerate them by hand.
- Recommended layout: `src/<project>/definitions.py` + `defs/<domain>/assets.py`
  per domain.
- Code locations are independently deployable Python environments; they share
  one UI.
- `dg scaffold` generates correct boilerplate so you start from a working
  skeleton, not a blank file.

## Next

[Unit 04 — Resources: Managed External Connections](../04-resources/README.md)
