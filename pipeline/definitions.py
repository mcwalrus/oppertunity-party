"""Root-level Dagster code location entry point.

``dg dev`` discovers this file via the ``[tool.dagster]`` section in
``pyproject.toml``.  All assets, jobs, and schedules are wired here.
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
from pipeline.defs.assets.pdf_html import pdf_html
from pipeline.defs.assets.pdf_images import pdf_images
from pipeline.defs.assets.pdf_validation import (
    validate_pdf_extraction,
    write_pdf_pipeline_report,
)
from pipeline.defs.assets.site import (
    site_blog,
    site_build,
    site_deploy,
    site_events,
    site_party_info,
    site_policies,
    site_sitemap_resolved,
    site_team,
)
from pipeline.defs.jobs import (
    full_pipeline,
    ingestion_job,
    pdf_html_job,
    pdf_job,
    site_deploy_job,
    transforms_job,
    validation_job,
)
from pipeline.defs.schedules import weekly_full_pipeline

defs = dg.Definitions(
    jobs=[
        full_pipeline,
        ingestion_job,
        transforms_job,
        pdf_job,
        pdf_html_job,
        site_deploy_job,
        validation_job,
    ],
    schedules=[weekly_full_pipeline],
    assets=[
        # ingestion layer
        raw_policies,
        raw_team,
        raw_blog,
        raw_events,
        raw_party_info,
        raw_pdfs,
        # clean layer
        clean_policies,
        clean_team,
        clean_blog,
        clean_events,
        clean_party_info,
        clean_pdfs,
        clean_index,
        # site layer (content → build → sitemap → deploy)
        site_policies,
        site_blog,
        site_events,
        site_team,
        site_party_info,
        site_build,
        site_sitemap_resolved,
        site_deploy,
        # validation layer (PDF extraction quality + coverage report)
        validate_pdf_extraction,
        write_pdf_pipeline_report,
        # PDF markdown → per-item HTML (runs after clean_pdfs)
        pdf_html,
        # PDF image extraction → clean/pdf-document/{slug}/images/
        pdf_images,
    ],
)
