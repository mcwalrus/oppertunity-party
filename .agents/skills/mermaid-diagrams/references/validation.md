# Mermaid Validation — CLI Workflow

The simplest way to validate Mermaid syntax is the CLI. If an SVG comes out, the
diagram is valid. If not, you have a parse error — no exit-code tricks needed.

---

## Installation (one-time)

```bash
npm install -g @mermaid-js/mermaid-cli
```

If you hit "Could not find Chromium" on first run:

```bash
npx puppeteer browsers install chrome
```

Or set `PUPPETEER_EXECUTABLE_PATH` to an existing Chrome/Chromium binary.

---

## Validate a file

```bash
mmdc -i diagram.mmd -o diagram.svg
```

- **SVG produced** → syntax is valid
- **No SVG + stderr error** → parse error; read the message

The signal is the output file, not an exit code.

---

## Quick one-liners (no file needed)

```bash
# Pipe a string
echo "flowchart LR\n  A --> B" | mmdc -i - -o /tmp/check.svg

# Pipe from clipboard (macOS)
pbpaste | mmdc -i - -o /tmp/check.svg

# Heredoc — most convenient when editing in-terminal
mmdc -i - -o /tmp/check.svg << 'EOF'
flowchart LR
  A[Start] --> B{Decision}
  B -->|yes| C[OK]
  B -->|no| D[Cancel]
EOF
```

All three forms: if `/tmp/check.svg` exists after the command, the diagram is valid.

---

## Reading parse errors

A typical error message:

```
Error: Parse error on line 2:
...LR  A[Start] --> end[Done]
----------------------^
Expecting 'NODE_STRING', ... got 'end'
```

| Part | What it means |
|------|---------------|
| `on line 2` | Where the parser was — **not necessarily where the bug is** |
| `...LR  A[Start] --> end[Done]` | The parser's view, truncated; the caret is where it gave up |
| `------^` | The column where parsing failed — the bug is at or just before this |
| `Expecting X, Y, got Z` | Tokens the parser would have accepted; the gap between expected and got is the fix |

---

## Pre-flight checklist

Run through this before committing a diagram:

- [ ] `mmdc -i x.mmd -o x.svg` passes (SVG produced)
- [ ] For `-beta` diagram types (`radar-beta`, `sankey-beta`, `xychart-beta`,
  `packet-beta`, `architecture-beta`), check that your target host actually renders
  them — GitHub doesn't render all of them yet
- [ ] Labels with `#` use `#35;` (e.g. `["Issue #35;42"]`)
- [ ] Labels with `"` use `#quot;` or rewritten to avoid the character
- [ ] `%%` comments are on their own lines, not appended after statements
- [ ] Edge labels use the pipe form (`---|text|`) not label-between-dashes (`-- text ---`)
- [ ] `stateDiagram-v2` (not `stateDiagram`)
- [ ] No `section` inside `sequenceDiagram` (use `rect rgb(...)` instead)
- [ ] No `classDef`/`class` inside `sequenceDiagram` or `block-beta` with `:::`
  (use `rect rgb(...)` for sequence; `class` + `classDef` separately for block)
- [ ] Reserved words as node ids are quoted: `A["end"]`, `A["class"]`, `A["graph"]`
- [ ] For `requirementDiagram`, `verifyMethod` is unquoted and SysML-cased:
  `Test`, `Analysis`, `Inspection`, `Demonstration`

---

## Per-diagram-type common errors

| Diagram | Common mistake | Fix |
|---------|---------------|-----|
| Flowchart | Label-between-dashes: `A -- text --- B` | Use `A ---|text| B` |
| Flowchart | Reserved word bare id: `end`, `graph`, `class` | Quote: `["end"]` |
| Sequence | Using `section` keyword | Use `rect rgb(...)` |
| Sequence | Using `classDef` / `class` / `:::` | Use `rect rgb(...)` for grouping |
| State | Using `stateDiagram` (v1) | Use `stateDiagram-v2` |
| Block | `:::` for class application | Use `class NodeName styleName` |
| Requirement | `verifyMethod: test` (lowercase) | Use `verifyMethod: Test` |
| Requirement | `verifyMethod: "Test"` (quoted) | Remove the quotes |
| XY Chart | `xychart` | Use `xychart-beta` |
| Sankey | `sankey` | Use `sankey-beta` |
| Radar | `radar` | Use `radar-beta` |
| Architecture | `architecture` | Use `architecture-beta` |
| Gantt | `after <id>` before id is defined | Define the referenced task first |
| Mindmap/Timeline | Inconsistent indentation | Use 2-space increments throughout |

---

## "Works on mermaid.live but fails elsewhere"

| Cause | Fix |
|-------|-----|
| Host doesn't support `-beta` types | Fall back to `flowchart` |
| Host is on an older Mermaid version | Check its version; use older syntax |
| `%%{init}%%` directive used | Replace with YAML frontmatter `config:` block |
| `securityLevel: strict` stripping HTML labels | Use `securityLevel: loose` or avoid HTML in labels |

---

## Batch validation across a codebase

When a repo has many `.md` files containing Mermaid blocks, use the bundled
script to extract and validate all of them in one pass.

**Requires `mmdc` — check first:**

```bash
which mmdc || echo "not installed"
```

If not installed, ask the user to run:

```bash
npm install -g @mermaid-js/mermaid-cli
# Then, if Chromium is missing:
npx puppeteer browsers install chrome
```

**Run the script:**

```bash
bash scripts/validate-diagrams.sh [directory]
```

- `directory` defaults to the current directory if omitted
- Walks all `.md` files recursively, extracts every ` ```mermaid ` block, and
  runs `mmdc` on each one
- Reports failures with source file and line number of the opening fence
- Exits non-zero if any block fails (suitable for CI)

**Example output:**

```
Found 175 Mermaid block(s) — validating with mmdc...

FAIL  ./docs/architecture.md:42
      Error: Parse error on line 3:

FAIL  ./docs/runbook.md:118
      Error: Lexical error on line 5. Unrecognized text.

Summary: 173 passed, 2 failed  (of 175 total)
```

Use this for one-off audits or as a CI step. For single-diagram checks, prefer
the one-liner `mmdc -i - -o /tmp/check.svg` approach — the batch script spins
up Chromium once per block and is slower.

---

## CI validation

```yaml
# GitHub Actions
- run: npm install -g @mermaid-js/mermaid-cli
- run: npx puppeteer browsers install chrome
- name: Validate standalone .mmd files
  run: |
    for f in $(find docs -name '*.mmd'); do
      mmdc -i "$f" -o "${f%.mmd}.svg" || {
        echo "::error file=$f::Diagram failed to parse"
        exit 1
      }
    done
- name: Validate Mermaid blocks in .md files
  run: bash scripts/validate-diagrams.sh docs
```

The `validate-diagrams.sh` step uses the bundled script and exits non-zero on
any failure, which fails the PR.
