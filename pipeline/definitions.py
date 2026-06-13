"""Root-level Dagster code location entry point.

``dg dev`` discovers this file via the ``[tool.dagster]`` section in
``pyproject.toml``.  All assets, jobs, and schedules are wired here once
they exist; for now the Definitions object is intentionally empty.
"""

import dagster as dg

from pipeline.defs.assets.clean import (
    clean_blog,
    clean_events,
    clean_index,
    clean_party_info,
    clean_pdfs,
    clean_policies,
    clean_team,
)
from pipeline.defs.assets.ingestion import (
    raw_blog,
    raw_events,
    raw_party_info,
    raw_pdfs,
    raw_policies,
    raw_team,
)
from pipeline.defs.assets.site import (
    site_blog,
    site_events,
    site_party_info,
    site_policies,
    site_team,
)
from pipeline.defs.jobs import full_pipeline, ingestion_job, pdf_job, transforms_job
from pipeline.defs.schedules import weekly_full_pipeline

defs = dg.Definitions(
    jobs=[full_pipeline, ingestion_job, transforms_job, pdf_job],
    schedules=[weekly_full_pipeline],
    assets=[
        raw_policies,
        raw_team,
        raw_blog,
        raw_events,
        raw_party_info,
        raw_pdfs,
        clean_policies,
        clean_team,
        clean_blog,
        clean_events,
        clean_party_info,
        clean_pdfs,
        clean_index,
        site_policies,
        site_blog,
        site_events,
        site_team,
        site_party_info,
    ],
)
