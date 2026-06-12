"""Dagster job definitions for the Opportunity Party pipeline."""

import dagster as dg

full_pipeline = dg.define_asset_job(
    name="full_pipeline",
    selection="*",
)

ingestion_job = dg.define_asset_job(
    name="ingestion_job",
    selection=dg.AssetSelection.groups("ingestion"),
)

transforms_job = dg.define_asset_job(
    name="transforms_job",
    selection=dg.AssetSelection.groups("clean", "site"),
)
