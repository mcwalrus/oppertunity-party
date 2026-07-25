#!/usr/bin/env bash
# validate-diagrams.sh
# Extract every ```mermaid``` block from every .md file under a directory and
# validate each one with mmdc. Reports pass/fail per block with source file and
# line number.
#
# Usage:
#   bash validate-diagrams.sh [directory]
#
# Arguments:
#   directory   Root to search for .md files (default: current directory)
#
# Requires:
#   mmdc  (@mermaid-js/mermaid-cli)
#   Install: npm install -g @mermaid-js/mermaid-cli
#   If Chromium is missing on first run: npx puppeteer browsers install chrome

set -euo pipefail

# ── Check for mmdc ────────────────────────────────────────────────────────────
if ! command -v mmdc >/dev/null 2>&1; then
  echo "Error: mmdc not found."
  echo ""
  echo "Install the Mermaid CLI first:"
  echo "  npm install -g @mermaid-js/mermaid-cli"
  echo ""
  echo "If Chromium is missing after install:"
  echo "  npx puppeteer browsers install chrome"
  exit 1
fi

# ── Arguments ─────────────────────────────────────────────────────────────────
SEARCH_DIR="${1:-.}"

if [ ! -d "$SEARCH_DIR" ]; then
  echo "Error: directory not found: $SEARCH_DIR"
  exit 1
fi

# ── Temp workspace ────────────────────────────────────────────────────────────
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

# ── Extract mermaid blocks ─────────────────────────────────────────────────────
idx=0
while IFS= read -r -d '' md_file; do
  in_block=0
  buf=""
  line_num=0
  block_start=0

  while IFS= read -r line; do
    line_num=$((line_num + 1))

    if [ "$line" = '```mermaid' ]; then
      in_block=1
      buf=""
      block_start=$line_num
      continue
    fi

    if [ "$line" = '```' ] && [ "$in_block" = "1" ]; then
      idx=$((idx + 1))
      block_id="$(printf '%04d' $idx)"
      printf '%s' "$buf" > "$WORK_DIR/$block_id.mmd"
      # Store source info: path and line where the block opened
      printf '%s:%d' "$md_file" "$block_start" > "$WORK_DIR/$block_id.src"
      in_block=0
      buf=""
      continue
    fi

    if [ "$in_block" = "1" ]; then
      buf="${buf}${line}
"
    fi
  done < "$md_file"
done < <(find "$SEARCH_DIR" -name '*.md' -print0 | sort -z)

# ── Nothing to validate ───────────────────────────────────────────────────────
if [ "$idx" -eq 0 ]; then
  echo "No Mermaid blocks found under $SEARCH_DIR"
  exit 0
fi

echo "Found $idx Mermaid block(s) — validating with mmdc..."
echo ""

# ── Validate each block ───────────────────────────────────────────────────────
fail=0
ok=0

for mmd_file in "$WORK_DIR"/*.mmd; do
  block_id="$(basename "${mmd_file%.mmd}")"
  src="$(cat "$WORK_DIR/$block_id.src")"

  if mmdc -i "$mmd_file" -o "${mmd_file%.mmd}.svg" \
       >/dev/null 2>"$WORK_DIR/$block_id.err"; then
    ok=$((ok + 1))
  else
    fail=$((fail + 1))
    echo "FAIL  $src"
    # Surface the first meaningful error line from mmdc stderr
    grep -E 'Parse error|Lexical error|Error:' "$WORK_DIR/$block_id.err" \
      | head -1 \
      | sed 's/^/      /'
    echo ""
  fi
done

# ── Summary ───────────────────────────────────────────────────────────────────
echo "Summary: $ok passed, $fail failed  (of $idx total)"
[ "$fail" -gt 0 ] && exit 1 || exit 0
