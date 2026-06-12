"""Dagster schedule definitions for the Opportunity Party pipeline."""

import dagster as dg

from pipeline.defs.jobs import full_pipeline

weekly_full_pipeline = dg.ScheduleDefinition(
    name="weekly_full_pipeline",
    job=full_pipeline,
    cron_schedule="0 6 * * 1",
)
