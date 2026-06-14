#!/usr/bin/env bash
# scripts/download.sh
#
# Download the entire Opportunity Party website as local markdown files.
# Output lands in .firecrawl/opportunity.org.nz/ (gitignored).
#
# Usage:
#   pnpm run download              # full site, up to 200 pages
#   LIMIT=50 pnpm run download     # override page limit
#   SECTION=/policies pnpm run download  # only a site section
#
# Requires FIRECRAWL_API_KEY in the environment (loaded by direnv via .envrc).

set -euo pipefail

SITE="https://www.opportunity.org.nz/"
LIMIT="${LIMIT:-200}"
SECTION="${SECTION:-}"

# Resolve the firecrawl binary (prefer local install)
FIRECRAWL="${FIRECRAWL_BIN:-$(dirname "$0")/../node_modules/.bin/firecrawl}"

if ! command -v "$FIRECRAWL" &>/dev/null && ! [ -x "$FIRECRAWL" ]; then
  echo "❌  firecrawl not found. Run: pnpm install" >&2
  exit 1
fi

if [ -z "${FIRECRAWL_API_KEY:-}" ]; then
  echo "❌  FIRECRAWL_API_KEY is not set. Run: direnv allow" >&2
  exit 1
fi

echo "🌐  Downloading: ${SITE}${SECTION}"
echo "    Limit: ${LIMIT} pages"
echo "    Output: .firecrawl/"
echo ""

ARGS=(
  x download "${SITE}${SECTION}"
  --only-main-content
  --limit "$LIMIT"
  -y
)

"$FIRECRAWL" "${ARGS[@]}"

echo ""
echo "✅  Download complete. Files saved to .firecrawl/"
echo "    Run 'pnpm run generate-llms' to build llms.txt and llms-full.txt."
