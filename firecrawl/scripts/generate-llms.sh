#!/usr/bin/env bash
# scripts/generate-llms.sh
#
# Build llms.txt and llms-full.txt from the markdown files downloaded by
# scripts/download.sh (.firecrawl/ directory).
#
# Output:
#   output/llms.txt        — site index (title + URL per page)
#   output/llms-full.txt   — full markdown content of every page
#
# There is no strict schema for llms.txt / llms-full.txt.
# The format follows the informal llmstxt.org convention but is intentionally
# flexible — agents will understand the content regardless of minor variations.
#
# Usage:
#   pnpm run generate-llms

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE_DIR="${ROOT_DIR}/.firecrawl"
OUTPUT_DIR="${ROOT_DIR}/output"
SITE_DIR="${SOURCE_DIR}/opportunity.org.nz"
SITE_URL="https://www.opportunity.org.nz"

LLM_INDEX="${OUTPUT_DIR}/llms.txt"
LLM_FULL="${OUTPUT_DIR}/llms-full.txt"

# ── Preflight ────────────────────────────────────────────────────────────────

if [ ! -d "$SOURCE_DIR" ]; then
  echo "❌  No .firecrawl/ directory found." >&2
  echo "    Run 'pnpm run download' first to fetch the site." >&2
  exit 1
fi

MARKDOWN_FILES=()
while IFS= read -r -d '' f; do
  MARKDOWN_FILES+=("$f")
done < <(find "$SOURCE_DIR" -name "*.md" -print0 | sort -z)

if [ "${#MARKDOWN_FILES[@]}" -eq 0 ]; then
  echo "❌  No markdown files found in .firecrawl/." >&2
  echo "    Run 'pnpm run download' first." >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

echo "📄  Found ${#MARKDOWN_FILES[@]} markdown files"
echo "    Building: output/llms.txt + output/llms-full.txt"
echo ""

# ── Helpers ──────────────────────────────────────────────────────────────────

# Convert a file path under .firecrawl/ to its site URL
file_to_url() {
  local filepath="$1"
  # Strip the .firecrawl/ prefix and .md suffix, then convert to URL
  local relative="${filepath#"$SOURCE_DIR/"}"
  # opportunity.org.nz/foo/index.md → /foo/
  relative="${relative#opportunity.org.nz}"
  relative="${relative%.md}"
  relative="${relative%/index}"
  # Ensure leading slash
  relative="/${relative#/}"
  # Root becomes /
  [ "$relative" = "/" ] || relative="${relative}/"
  echo "${SITE_URL}${relative}"
}

# Extract the first H1 heading from a markdown file, fallback to filename
file_to_title() {
  local filepath="$1"
  local title
  title=$(grep -m1 '^# ' "$filepath" 2>/dev/null | sed 's/^# //' || true)
  if [ -z "$title" ]; then
    # fallback: derive title from path
    title=$(basename "$(dirname "$filepath")")
    [ "$title" = "opportunity.org.nz" ] && title="Home"
  fi
  echo "$title"
}

# ── llms.txt ─────────────────────────────────────────────────────────────────
# Format:
#   # <Title>
#   > <URL>
#   (blank line between entries)

{
  echo "# Opportunity Party — Site Index"
  echo "> Generated: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "> Source: ${SITE_URL}"
  echo ""
  echo "---"
  echo ""

  for filepath in "${MARKDOWN_FILES[@]}"; do
    title=$(file_to_title "$filepath")
    url=$(file_to_url "$filepath")
    echo "## ${title}"
    echo "> ${url}"
    echo ""
  done
} > "$LLM_INDEX"

echo "✅  output/llms.txt        (${#MARKDOWN_FILES[@]} pages)"

# ── llms-full.txt ────────────────────────────────────────────────────────────
# Format:
#   # <Title>
#   > <URL>
#   (blank line)
#   <full markdown content>
#   ---
#   (repeat)

{
  echo "# Opportunity Party — Full Site Content"
  echo "> Generated: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "> Source: ${SITE_URL}"
  echo "> Pages: ${#MARKDOWN_FILES[@]}"
  echo ""
  echo "---"
  echo ""

  for filepath in "${MARKDOWN_FILES[@]}"; do
    title=$(file_to_title "$filepath")
    url=$(file_to_url "$filepath")

    echo "## ${title}"
    echo "> ${url}"
    echo ""
    cat "$filepath"
    echo ""
    echo "---"
    echo ""
  done
} > "$LLM_FULL"

echo "✅  output/llms-full.txt   ($(du -sh "$LLM_FULL" | cut -f1))"
echo ""
echo "Done. Commit these files intentionally if you want a versioned snapshot."
