---
name: tech-course
description: >
  Generate a complete, mental-model-first course on any technology — a landing
  README, a CHEATSHEET, and dependency-ordered numbered course units, each
  following a fixed learn → why → concepts → exercises → self-checks → takeaways
  template, grounded in primary sources before any content is written and with
  the syllabus confirmed first.
  Trigger on "create a course on X", "build a tutorial for X", "teach me X from
  the ground up", "write a ground-up course about X", or /tech-course. Do NOT
  trigger for producing a mental-model review from official docs — use
  tech-doc-research for that. Do NOT trigger for touring an existing repo or
  codebase — use tech-guide for that. Do NOT trigger for finding or comparing
  libraries and tools — use tech-stack-research for that.
user-invocable: true
---

# Tech Course Builder

Produce a complete, ground-up course on a technology for working engineers —
mental-model-first, dependency-ordered, and immediately runnable. The course is
a multi-file tree: a landing `README.md`, dependency-ordered units under
`course/`, and a `CHEATSHEET.md` they keep using after they finish. The single
load-bearing property is that each unit depends only on earlier ones and anchors
every new concept to something the reader already knows. Success looks like a
course a fluent-but-new engineer can follow top to bottom without ever hitting a
forward reference, and a cheatsheet that survives as a day-to-day reference.

## Values

- **Dependency-correctness over coverage.** A unit that forward-references a
  later concept is a defect. Getting the order right matters more than including
  every feature.
- **Mental models over feature enumeration.** Teach the load-bearing intuitions
  first; features hang off them.
- **Anchored analogy over abstract explanation.** Relate each new idea to a tool
  the reader already uses, then state explicitly where the analogy breaks down.
- **Opinionated over neutral.** State "avoid X", "use Y for new projects" — but
  only from grounded knowledge. Every recommendation traces to a primary source
  (see Workflow Step 2), never to memory. A course that refuses to recommend
  wastes the reader's judgment budget; a course that recommends from a guess
  misleads it.
- **Minimal runnable snippets over prose.** Every snippet does one thing and is
  copy-pasteable, with expected output shown as a `→ result` comment in the
  snippet's native comment syntax.

## Constraints

- Never generate full unit content before the user confirms the syllabus — the
  unit list (titles + one-line practical goal each) and the 3–5 core mental
  models. This checkpoint is what keeps units dependency-correct; skipping it is
  the one unrecoverable failure.
- Resolve the audience background before generating anything. Every analogy and
  every "this surprises everyone coming from X" aside anchors to it. If it is
  not stated and not obvious from context, ask.
- Never propose a syllabus or write content from memory alone. Ground in primary
  sources first — `tech-doc-research` for concepts, `fresh-data` for versions,
  setup commands, and recommendations — for every course, however well you know
  the technology. The syllabus and content must derive from that research, not
  merely follow it. See Workflow Step 2 and `references/grounding-workflow.md`,
  which also defines the fallback when sources are thin so the skill never
  deadlocks on its own precondition.
- Before writing, check the target. Write directly only if the files you would
  overwrite are tracked and committed (so `git checkout` restores them). If the
  target is not a git working tree, OR the colliding file is untracked or has
  uncommitted changes, do not overwrite: write into a dedicated
  `./<technology>-course/` subdirectory, or confirm with the user first.
- Every unit depends only on earlier units. Foundational units come first and
  are marked non-skippable.
- Every unit follows the per-unit template in Output Format exactly — same
  section order, every time, so readers always know where to look.
- Do not explain what the audience already knows (terminals, variables). Do
  explain everything specific to the technology from first principles.

## Workflow

1. **Establish subject and audience.** Identify the technology and what the
   reader already knows (their existing tools and background). Infer the
   audience from context when obvious; otherwise ask. Pick a unit count that
   fits the subject's real surface area — typical courses run 5–12 units; go
   lower for narrow tools, higher only for genuinely broad platforms. Never pad.

2. **Ground in primary sources.** Before proposing the syllabus, ground the
   course — never work from memory alone. Run `tech-doc-research` for the core
   concepts and mental models, and `fresh-data` for the version-sensitive slice
   (current version, setup commands, and every opinionated recommendation). The
   syllabus and content must derive from this research, not merely follow it in
   time. See `references/grounding-workflow.md` for the tool split, the data
   flow, and the fallback ladder when sources are thin or unreachable.

3. **Propose the syllabus and stop.** Present, for confirmation:
   - The unit list as a table: `| Unit | Topic | Practical goal |`, ordered so
     each unit depends only on earlier ones.
   - The 3–5 core mental models (one bolded sentence + 2–3 lines each), drawn
     from the Step 2 research — note where each came from.
   Do not write any unit body until the user confirms or adjusts. This is the
   single gate.

4. **Generate in order.** On confirmation: write the landing `README.md` first,
   then each unit in dependency order, then the `CHEATSHEET.md`. Keep each unit
   focused — roughly 350 lines or fewer. Every opinionated recommendation and
   setup command carries its Step 2 grounding.

5. **Choose the write location, then write.**
   (a) Base dir = the dir the user names, else cwd.
   (b) Apply the write-safety constraint: if the files you would overwrite are
       tracked and committed, write directly; otherwise write into
       `./<technology>-course/`, or confirm with the user first. Never silently
       overwrite.
   (c) Write `README.md` → units in dependency order → `CHEATSHEET.md`.

## Output Format

The course tree:

```
.
├── README.md                 # landing page: map, prerequisites, setup, mental models
├── CHEATSHEET.md             # single-page command + template reference
└── course/
    ├── 01-<slug>/README.md   # Unit 01 — foundational, non-skippable
    ├── 02-<slug>/README.md   # builds on 01
    └── NN-<slug>/README.md   # final unit — real-world / production patterns
```

**Landing `README.md`**, in this order:
1. One-paragraph framing — who it is for, how units build.
2. "Course Structure" table `| Unit | Topic | Practical goal |`, one row per
   unit, each Unit cell linking to `course/NN-<slug>/README.md`.
3. "Prerequisites" — what they must know; explicitly list what they do NOT need.
4. Installation / setup — copy-paste commands plus a verify step.
5. "Core Mental Models (Read Before Unit 1)" — the confirmed 3–5 ideas.
6. Recommended sequence — group units into phases; say where to spend time.
7. "Key Reference Commands" — the most-used commands, each commented.

**Each unit `course/NN-<slug>/README.md`** follows EXACTLY this template:
- `# Unit NN — <Title>`
- `## What you will learn` — 4–6 bullet outcomes.
- `## Why this unit exists` — motivation; what breaks if you skip it.
- Numbered concept sections (`## 1.`, `## 2.`, …). Each: name the concept, show
  the smallest runnable snippet that demonstrates it, then explain. Use inline
  asides for what "surprises everyone coming from <audience>". Show expected
  output with a `→ result` comment in the snippet's native comment syntax
  (`#`, `//`, `--`, etc.).
- `## Practical Exercises` — 2–4 hands-on tasks the reader runs themselves.
- `## Self-Check` — 3 questions whose answers are derivable from this unit.
- `## Key Takeaways` — 4–6 crisp bullets.
- `## Next` — link to the following unit.

**`CHEATSHEET.md`**:
- Grouped, commented command blocks (divide with `# ── SECTION ──`).
- Copy-paste templates for the most common artifacts in the technology.
- At least one decision table (when to use X vs Y).
- A "Common Gotchas" table `| Symptom | Likely cause |`.

**Style rules** (apply throughout):
- Minimal, runnable, copy-pasteable code over prose; one thing per snippet.
- Relate new ideas to the reader's existing tools by analogy, then say where it
  breaks down.
- No filler, no "in this section we will" — get to the concept.
- Use GFM tables for comparisons, placements, and gotchas.
- Put real-world / production patterns in the later units, not just toy examples.

## Transitions

Grounding in primary sources is not optional and not a fallback — it is Workflow
Step 2, run for every course regardless of how well you know the technology. See
`references/grounding-workflow.md` for the full procedure: the `tech-doc-research`
/ `fresh-data` split, how research feeds the syllabus and content, and the
fallback ladder when sources are thin or unreachable. For touring an existing
codebase rather than teaching a technology from the ground up, hand off to
`tech-guide` instead.
