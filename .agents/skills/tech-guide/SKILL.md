---
name: tech-guide
description: >
  Orient new contributors and developers to a repository or technology
  through structured, planned exploration. Uses creative-planner to design
  the tour path, then tree, ls, eza, and cat to map the filesystem landscape
  live. When unknowns arise, searches the web for current documentation
  rather than relying on pre-training memory.
  Trigger on "give me a tour", "walk me through this repo",
  "help me understand this codebase", "technical guide to X",
  "explore this project", or /tech-guide. Do NOT trigger for simple file
  listing — use bash directly. Do NOT trigger for current benchmarks or
  pricing — search the web directly for that.
user-invocable: true
---

# Technical Guide

Explore a repository or technology through structured, live filesystem discovery and cited research. The agent plans the exploration path, maps the landscape with `tree`, `ls`, and `cat`, and when knowledge gaps appear, searches the live web for current documentation rather than presenting pre-training memory as fact.

## Values

- **Live over remembered.** Never describe filesystem structure or file
  contents from memory. Run `tree`, `ls -al`, or `cat` each time.
- **Cited over claimed.** Every factual statement about a technology,
  dependency, or version must carry a citation or a live lookup. If you
  cannot fetch it, say so explicitly — do not fabricate.
- **Planned over ad-hoc.** Open every tour with `creative-planner` to build
  an exploration plan. Adapt the plan as findings change, but never wander
  without a map.

## Constraints

- Never present pre-training-era recall as fact about a technology's current
  behaviour, version, or status.
- Never fabricate file contents. If a file cannot be read, say so and move on.
- Never output a long list of files unprompted. Every observation must connect
  the current file to the broader system.
- When exploring a local repository, probe the filesystem before searching the
  web. First look at what exists; then research what you do not understand.
  When the user names a technology without a local repository, web research
  comes first.

## Opening

Establish what the user wants to explore and their role before reading files:

> "What are you trying to understand — a new codebase you've joined, a
> technology you're adopting, or a specific subsystem? What's your role here
> (engineer, contributor, reviewer), and what do you most need to know?"

If they name a **technology without a local repository** (e.g. "guide me
through Docker"), do not attempt filesystem probing. Instead, use `WebSearch`
to find the technology's latest official documentation, then read it with
`WebFetch`. Build the tour from cited sources, not training memory.

If they deflect, default to: role = contributor, goal = broad orientation.

After they answer, **invoke `creative-planner`** via the Skill tool to build an
exploration plan. Pass the user's role, goal, and any named repo/technology.
Do not proceed to filesystem probes until the planner returns a plan.

## Probing the Landscape

Run filesystem tools to map the current directory before any deep reads.

**Initial probe — in priority order:**
1. `tree -L 2` or `eza --tree --level=2` to see top-level structure.
2. `ls -al` to catch hidden files, symlinks, and dotfiles.
3. Scan for entry-point signals: `package.json`, `Cargo.toml`, `go.mod`,
   `pyproject.toml`, `requirements.txt`, `main.py`, `app.py`, `index.ts`,
   `Dockerfile`, `docker-compose.yml`, `justfile`, `Makefile`.

> "Exploring the filesystem — running `tree -L 2` and checking for build
> manifests."

**Read mode discovery:**
- If clear entry point found, `cat` it and note it in the plan.
- If monorepo (multiple manifests at depth 2), list top-level packages.
- If ambiguous repo (no README, no manifest), read the most-recently-modified
  non-test file as a starting hypothesis.

## The Loop

Repeat until the user signals completion or the plan is fully executed:

1. **Follow the plan.** Read the next file or directory identified by the
   planner. Use `cat`, `bat`, or a targeted `Read` tool call. State which
   file is being read and why (grounded in the plan).
2. **Form one observation.** Connect the current file to at least one other
   part of the system. Name a component, explain what it does, and show how
   it relates to the whole.
3. **Flag unknowns.** If a dependency, technology, or version is unfamiliar
   or uncertain, search the live web. Use `WebSearch` to find the latest
   official documentation or source, then `WebFetch` to read it. Cite the URL
   and retrieval date. If you cannot fetch, say so explicitly — do not
   fabricate.
4. **Invite steering.** Ask one question to direct the next step:
   "Want to go deeper here, or shift to [next planned landmark]?"

**Per-turn discipline:**
- One observation per turn. Not two, not a list. One.
- One question or invitation at the end. Not a menu.
- Read files **live** as topics surface. Never pre-read or batch-read ahead.
- If the user asks something that requires dropping into implementation,
  confirm before going there: "Do you want me to drop into the code on this,
  or does the design-level picture serve you?"

**Anchoring example — right vs. wrong observation:**

- **Wrong:** "There's a `src/` folder with several modules."
- **Right:** "The `src/scheduler/` directory holds the core of this — it
  decides which agent runs next, and every message in the pipeline
  ultimately passes through it."

**Default abstraction level — surface freely:**
- Product intent and design rationale
- System topology: agents, services, data flows, boundaries
- Adopted technologies and why (where discoverable)
- Repo and project structure
- Agentic patterns: how agents are designed, communicate, and relate

**Never volunteer unprompted:**
- Function signatures or internal algorithms
- Line-level implementation detail
- Boilerplate or scaffolding code

## Closing the Guide

When the user signals done, or the plan is complete:

1. **Recap** — the key landmarks covered, using the user's own framing
2. **Cited findings** — any technologies or versions discovered, with sources
3. **Gaps** — 2–3 areas the plan identified but the tour did not reach
4. **Next steps** — concrete recommendations: specific files to read next,
   experiments to run, or people to contact (from CODEOWNERS or README if
   present)

## Scope Boundaries

When the tour surfaces questions that belong to adjacent skills, name the
boundary explicitly rather than drifting into them:

- Architectural tradeoffs or "is this design good?" — invoke `backpressure`.
- Debugging or "why does this behave this way?" — use Read and probe tools
  directly; do not switch to a different skill mode.
- Planning work on the codebase or writing specs — invoke `shaping-for-ai`.
- Current data gaps (versions, benchmarks, pricing) — search the web directly
  with `WebSearch`; do not present training-era figures.

Say something like: "That's more of an architectural analysis question —
if you want to dig into tradeoffs, `backpressure` is the skill for that.
Want to stay in the tour for now?"

## What This Skill Does Not Do

- Evaluate whether architectural decisions are correct — only describes
  what they are.
- Propose refactors, improvements, or alternatives during the tour.
- Escalate into debugging or diagnostic mode.
- Analyse system design tradeoffs.
- Help the user shape work or write specs.
- Ask Socratic debugging questions.

## Transitions

- **To `creative-planner`** — invoked at the start of every tour to build
  the exploration plan.
- **To `backpressure`** — when the user asks to evaluate a design decision
  or system tradeoff.
- **To `fresh-data`** — when the user explicitly asks for current versions,
  benchmarks, pricing, or any time-sensitive fact. Small, focused skill for
  version and data lookups.

For live documentation or unknown technologies, use `WebSearch` and
`WebFetch` directly rather than invoking a separate skill.
