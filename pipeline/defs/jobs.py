"""Dagster job definitions for the Opportunity Party pipeline."""

import dagster as dg

from pipeline.defs.partitions import policy_slug_partitions

# PDF assets are partitioned by policy slug and managed separately via pdf_job.
_pdf_assets = dg.AssetSelection.assets("raw_pdfs") | dg.AssetSelection.assets("clean_pdfs")

# site_deploy is excluded from full_pipeline because it is a production-affecting
# action (publishes to Cloudflare Workers).  Launch it explicitly via
# site_deploy_job.
_production_assets = dg.AssetSelection.assets("site_deploy")

full_pipeline = dg.define_asset_job(
    name="full_pipeline",
    # Excludes partitioned PDF assets (run pdf_job per partition) and the
    # production-affecting site_deploy asset (use site_deploy_job).
    selection=dg.AssetSelection.all() - _pdf_assets - _production_assets,
)

ingestion_job = dg.define_asset_job(
    name="ingestion_job",
    # raw_pdfs is partitioned; excluded here so this job remains unpartitioned.
    selection=dg.AssetSelection.groups("ingestion") - dg.AssetSelection.assets("raw_pdfs"),
)

transforms_job = dg.define_asset_job(
    name="transforms_job",
    # clean_pdfs is partitioned; excluded here so this job remains unpartitioned.
    selection=dg.AssetSelection.groups("clean", "site") - dg.AssetSelection.assets("clean_pdfs"),
)

pdf_job = dg.define_asset_job(
    name="pdf_job",
    description=(
        "Download and clean PDFs for a single policy slug. "
        "Select a partition (policy slug) when launching this job."
    ),
    selection=_pdf_assets,
    partitions_def=policy_slug_partitions,
)

site_deploy_job = dg.define_asset_job(
    name="site_deploy_job",
    description=(
        "Deploy the static site to Cloudflare Workers via wrangler. "
        "Production-affecting — run after site_build and site_sitemap_resolved "
        "have materialised (full_pipeline handles both automatically)."
    ),
    selection=dg.AssetSelection.assets("site_deploy"),
)

validation_job = dg.define_asset_job(
    name="validation_job",
    description=(
        "Validate PDF→markdown extraction quality and regenerate "
        "docs/pdf-pipeline.md. Reads every PDF in data/sources/"
        "opportunity-website/pdfs/ — does not modify policy content. "
        "Run after pdf_job (per policy slug) has materialised the "
        "extracted markdown."
    ),
    selection=dg.AssetSelection.assets("validate_pdf_extraction", "write_pdf_pipeline_report"),
)
