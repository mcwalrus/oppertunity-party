"""Dagster job definitions for the Opportunity Party pipeline."""

import dagster as dg

from pipeline.defs.partitions import policy_slug_partitions

# PDF assets are partitioned by policy slug and managed separately via pdf_job.
_pdf_assets = dg.AssetSelection.assets("raw_pdfs") | dg.AssetSelection.assets("clean_pdfs")

full_pipeline = dg.define_asset_job(
    name="full_pipeline",
    # Excludes partitioned PDF assets — run pdf_job per partition for those.
    selection=dg.AssetSelection.all() - _pdf_assets,
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
