"""Dagster partition definitions for the Opportunity Party pipeline."""

import dagster as dg

from pipeline.ingestion.policies import POLICY_SLUGS

# One partition per policy slug — drives per-policy PDF ingestion and clean.
# Sorted for stable ordering in the Dagster UI.
policy_slug_partitions: dg.StaticPartitionsDefinition = dg.StaticPartitionsDefinition(
    sorted(POLICY_SLUGS.keys())
)
