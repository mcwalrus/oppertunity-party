# How I learn from a repo using graphify + context-mode + pi

Companion to `ACTIONS.md`, `CHEATSHEET.md`, `NEXT_STEPS.md`. One diagram per question.

## 1. System map — what each tool owns

The repo, graphify, context-mode, and pi are four boxes with one job each. The agent
threads them together.

```mermaid
flowchart TB
    subgraph REPO["Repo"]
        SRC["~500 source files"]
    end

    subgraph GRAPHIFY["graphify"]
        BUILD["update ."]
        QUERY["query / path / explain"]
        GJSON[("graph.json")]
    end

    subgraph CM["context-mode"]
        BATCH["ctx_batch_execute"]
        SEARCH["ctx_search"]
        FTS[("FTS5 index")]
    end

    subgraph PI["pi harness"]
        AGENT["Agent"]
    end

    BUILD -->|AST extract| SRC
    BUILD -->|writes| GJSON
    QUERY -->|reads| GJSON
    QUERY -->|stdout| BATCH
    BATCH -->|indexes| FTS
    SEARCH -->|BM25 query| FTS
    SEARCH -->|snippets| AGENT
    AGENT -->|runs| BUILD
    AGENT -->|runs| QUERY
    AGENT -->|runs| BATCH
    AGENT -->|runs| SEARCH
```

**Takeaway:** graphify owns the *index* (`graph.json`), context-mode owns the *cache*
(FTS5 over stdout), the agent owns the *loop* (run → read → synthesize → repeat).
No tool does another's job.

---

## 2. Investigation sequence — what happened in this session

What you saw me do, decomposed.

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant A as Agent
    participant G as graphify
    participant C as context-mode
    participant R as Repo

    U->>A: "how are you learning from queries?"
    A->>R: read graphify/ACTIONS.md
    Note over A: understand prior session
    A->>G: graphify update .
    G->>R: AST extract code files
    G-->>A: 3197 nodes, 3714 edges
    A->>C: ctx_batch_execute
    C->>G: spawn N commands in parallel
    G->>R: read graph.json
    G-->>C: JSON per command
    C->>C: index to FTS5
    C-->>A: matched sections inline
    A->>A: synthesize answer
    A->>U: multi-section summary
```

**Takeaway:** the agent doesn't *read* the graph — it *queries* it, wraps the
queries so context-mode caches them, then retrieves specific sections by
topic. One round trip, not N.

---

## 3. Tool picker — which graphify command for which question

```mermaid
flowchart LR
    Q["Question about the repo"]

    Q -->|"what hubs exist?"| GN["god-nodes"]
    Q -->|"how does X connect to Y?"| P["path A B"]
    Q -->|"show me everything around X"| E["explain X"]
    Q -->|"natural-language search"| QU["query phrase"]

    Q -->|"refresh after code edits"| U["update ."]
    Q -->|"fresh build"| B["graphify ."]
```

**Takeaway:** `path` and `explain` are *structural* (graph topology);
`query` is *semantic* (BM25 over node text). `god-nodes` is a bird's-eye
view. Pick the verb, then the noun.

---

## 4. Before / after — why `graph.json` is a shortcut

```mermaid
flowchart TB
    subgraph Before["Without graph.json"]
        AF["Agent"]
        AF -->|"file 1"| F1["f1"]
        AF -->|"file 2"| F2["f2"]
        AF -->|"..."| F3["f3"]
        AF -->|"file N"| FN["fN"]
    end

    subgraph After["With graph.json"]
        AG["Agent"]
        AG -->|"query"| GJ["graph.json"]
        GJ -->|"ranked subgraph"| AG
    end
```

**Takeaway:** `graph.json` is a *precomputed* index over the corpus. The agent
trades N file reads for 1 graph query + 1 retrieval. That's the whole
reason the tool exists — turning *read the world* into *ask the world*.

---

## Reading order

1. Diagram 1 (roles) — orient yourself in the system.
2. Diagram 2 (sequence) — see one full investigation cycle.
3. Diagram 3 (picker) — know which command to use when.
4. Diagram 4 (shortcut) — understand *why* this is fast.