# Grounding Workflow

The detailed procedure for **Workflow Step 2**. The tech-course skill never
proposes a syllabus or writes content from memory alone — it grounds the course
in primary sources first, for every technology, regardless of how well it is
already known.

## Why this is mandatory, not conditional

A course teaches. An error in a course propagates to every learner who follows
it. The most dangerous case is not "I don't know this technology" — that is
obvious and self-correcting. It is "I sort of know this": shallow familiarity
that produces confident, opinionated, wrong advice and feels grounded enough to
skip the check. Unconditional grounding closes that gap. It costs a research pass
on technologies you know well — the deliberate, accepted price of never shipping
ungrounded confidence in a teaching artifact.

## Two layers, two tools

Grounding has two distinct layers. Use the right tool for each — they are not
interchangeable, and mandating both without dividing their work invites the agent
to apply the wrong one.

| Layer | Tool | What it grounds |
|---|---|---|
| Conceptual | `tech-doc-research` | Core abstractions, architecture, data flow, execution model, the 3–5 mental models — the spine of the course |
| Time-sensitive | `fresh-data` | Current stable version, install / setup commands, deprecations, and every opinionated "use Y for new projects" recommendation |

`tech-doc-research` builds the mental models. `fresh-data` keeps the
version-sensitive and opinionated claims from rotting — these are exactly the
facts a teaching artifact must not get wrong, and exactly the ones that go stale
in training data. A course on a stable concept (e.g. ownership semantics) leans
on `tech-doc-research` for its spine and on `fresh-data` only for the toolchain
and edition facts.

## Procedure

1. **Run `tech-doc-research` on the technology.** Take its structured
   mental-model review as the source for the syllabus's core concepts and
   dependency ordering. The 3–5 mental models proposed at the syllabus gate come
   from here, not from memory.
2. **Run `fresh-data` for the version-sensitive slice** — current stable version,
   the canonical install / setup commands, current deprecations, and any
   "use X / avoid Y" recommendation the course intends to make. Every opinionated
   claim must trace to a live source.
3. **Carry the grounding forward.** The syllabus proposal states which mental
   models came from the doc review. The setup commands and opinionated
   recommendations in the README and units carry their `fresh-data` grounding.
   Running the research is the means; grounding the artifact is the requirement —
   research you ran but did not use is wasted, and re-opens the very gap this step
   exists to close.

## Fallback ladder — when grounding is thin or unreachable

Grounding is mandatory, but it can fail: a technology may have sparse or no
official docs, be internal / proprietary, or `fresh-data` lookups may be blocked.
The skill must never deadlock on its own precondition. Apply in order:

1. **Thin docs.** Ground what you can. For concepts the docs do not cover, say so
   in the syllabus proposal and flag which units rest on weaker grounding.
2. **No public docs (proprietary / internal).** Ask the user for the primary
   source — a link, a repo, a spec. If none exists, state plainly that the course
   will rest on your own knowledge and ask the user to confirm before proceeding.
3. **Lookups blocked (no network / rate-limited).** Surface it. Do not silently
   fall back to memory for version-sensitive claims — instead mark every version
   number and setup command as "verify against current docs" in the output so the
   reader knows what was not grounded.

The single rule under all three: **never silently substitute memory for
grounding.** If grounding is unavailable, the output says so.
