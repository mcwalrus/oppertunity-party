# Documentation Patterns

Worked examples of the 7 patterns for composing diagrams in PRs, ADRs, and RFCs.
Running example: **adding a response cache layer behind a feature flag**.

---

## Pattern 1 — Layered ownership

**Question:** *Who owns what code? Which layer does what?*

Use when introducing a new layer between existing ones. Subgraphs = ownership boundaries.

```mermaid
flowchart TB
    subgraph Handler["API Handler"]
        H[handleRequest]
    end
    subgraph Cache["Response Cache (new)"]
        CC[CacheClient]
        CM[CacheMetrics]
    end
    subgraph Backend["Upstream Backend"]
        B[BackendService]
    end
    H -->|get key| CC
    CC -->|miss| B
    B -->|response| CC
    CC --> CM
    CC -->|hit| H
```

**Anti-pattern:** a flat list of nodes without subgraphs — readers can't tell who owns what.
**Note:** subgraph `direction` is overridden when any node inside connects outside. Set direction on the parent.

---

## Pattern 2 — Data flow / transformation

**Question:** *What does the data look like at each step?*

Use for request-shape transformations, key derivation, normalization pipelines. Always include branch labels so both outcomes are visible.

```mermaid
flowchart LR
    REQ["GET /users/42?fields=email"] --> NORM["normalize\nstrip fields"]
    NORM --> KEY["sha256(userID)\ncache key"]
    KEY --> LOOKUP["cache.Get(key)"]
    LOOKUP -->|hit| SERVE["serve cached response"]
    LOOKUP -->|miss| FETCH["backend.Fetch"]
    FETCH --> STORE["cache.Set(key, ttl)"]
    STORE --> SERVE
```

**Anti-pattern:** a single node labeled "process request" — that's where the interesting transformations live.

---

## Pattern 3 — Async fan-in / dedupe

**Question:** *What happens when N callers arrive at once?*

Use for caches, request coalescers, async job dispatchers. `par/and` shows concurrent callers; `alt/else` shows branch outcomes.

```mermaid
sequenceDiagram
    autonumber
    participant C1 as Caller 1
    participant C2 as Caller 2
    participant H as Handler
    participant CC as CacheClient
    participant B as Backend

    par concurrent requests
        C1->>H: GET /users/42
        H->>CC: Get(key)
        CC-->>H: miss
        H->>B: Fetch(42)
    and
        C2->>H: GET /users/42
        H->>CC: Get(key)
        CC-->>H: miss
        Note over CC,B: dedupe on inflight map
    end
    B-->>H: response
    H->>CC: Set(key, response, ttl)
    H-->>C1: 200 + body
    H-->>C2: 200 + body
```

**Note:** `par/and` branches *share* the rest of the diagram — only the inside of `par` is concurrent.

---

## Pattern 4 — Before / after

**Question:** *What changed?*

Use dotted edges (`-.->`) for *new* paths, solid for *existing*. The visual contrast makes the change scannable.

```mermaid
flowchart LR
    subgraph Before["Before — no cache"]
        B1[Handler] -->|every request| BE1[Backend]
    end
    subgraph After["After — cache in front"]
        A1[Handler] -->|key| AC1[Cache]
        AC1 -->|miss| BE2[Backend]
        AC2[Cache] -.->|hit| A1
    end
```

**Anti-pattern:** drawing only the "after" state — readers see the new design but miss what was replaced.

---

## Pattern 5 — Config evolution

**Question:** *How is config structured, and which container owns which resource?*

Use for config refactors, coupling fixes, resource boundary changes.

```mermaid
flowchart TB
    subgraph Bug["Before — shared counter"]
        BC1[Config.MaxBytes]
        BC2["userCache + sessionCache\nboth write totalBytes"]
        BC1 --> BC2
    end
    subgraph Fixed["After — per-cache config"]
        FC3[Config]
        FC1[UserCacheConfig]
        FC2[SessionCacheConfig]
        FC3 --> FC1
        FC3 --> FC2
        FC1 -.-|independent totalBytes| FC2
    end
```

**Anti-pattern:** listing config keys as bullets — the diagram shows what depends on what.

---

## Pattern 6 — Object lifecycle

**Question:** *What states does this object live in?*

Use `stateDiagram-v2` for objects with more than two states — cache entries, jobs, deployments, connections, requests.

```mermaid
stateDiagram-v2
    [*] --> Empty: NewEntry(key)
    Empty --> Fetching: Get(key) + miss
    Fetching --> Cached: backend response
    Fetching --> Empty: backend error
    Cached --> Expired: TTL elapsed
    Cached --> Evicted: LRU eviction
    Expired --> Empty: Get(key)
    Evicted --> Fetching: Get(key) + miss
    note right of Fetching
        inflight map dedupes
        concurrent Gets
    end note
```

**Anti-pattern:** using a sequence diagram for lifecycle — sequence shows messages, state shows states.

---

## Pattern 7 — Migration path

**Question:** *How do we get from old to new?*

Three subgraphs in order: Before → Flagged → After. Makes rollout states impossible to confuse.

```mermaid
flowchart LR
    subgraph Before["Before"]
        BH[Handler] --> BB[Backend]
    end
    subgraph Flagged["Feature flag on"]
        FF["config.cacheEnabled"]
        FH[Handler] -->|if flagged| FC[Cache]
        FH -->|not flagged| FBB[Backend]
        FC --> FB[Backend]
    end
    subgraph After["Flag removed"]
        AH[Handler] --> AC[Cache]
        AC --> AB[Backend]
    end
    Before --> Flagged
    Flagged --> After
```

**Tip:** a dashed edge into a phantom node (`X[" "]`) communicates "this path is gone" without prose.
**Anti-pattern:** describing the rollout in prose only — the three subgraphs make the states visually distinct.

---

## Combining patterns in one doc

A typical PR description uses 3–5 patterns interleaved with prose:

```markdown
## Context
[2–3 lines: what's the problem?]

## Proposed change
[2–3 lines: what's the new shape?]

### Layering        ← Pattern 1: who owns what
[diagram]

### Data flow       ← Pattern 2: what does the request look like
[diagram]

### Hot path        ← Pattern 3: concurrency
[diagram]

### Lifecycle       ← Pattern 6: cache entry states
[diagram]

### Rollout         ← Pattern 7: Before → Flagged → After
[diagram]
```

**Rule:** one diagram per *question*, not per artifact or code module.
Pair every diagram with a 1–2 sentence caption.

---

## Observability templates

**Request trace (L3):**
```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant API as API Gateway
    participant Svc as Service
    participant DB

    U->>API: POST /checkout
    API->>Svc: POST /charge
    Svc->>DB: INSERT payment
    Note over DB: 1,200ms ⚠
    DB-->>Svc: row inserted
    Svc-->>API: 201 (1,250ms)
    API-->>U: 201
```

**Incident timeline (L1 logs):**
```mermaid
gantt
    title Incident timeline
    dateFormat HH:mm
    axisFormat %H:%M
    section Detection
        Alert fired        :done, a1, 14:02, 2m
        On-call paged      :done, a2, after a1, 1m
    section Investigation
        Identified DB lock  :done, a3, after a2, 18m
    section Mitigation
        Killed long queries :crit, a4, after a3, 5m
        Traffic recovered   :done, a5, after a4, 3m
```

**Alert routing chain:**
```mermaid
sequenceDiagram
    participant M as Metric
    participant AM as AlertManager
    participant PD as PagerDuty
    participant OC as On-call
    M->>AM: breach detected
    AM->>PD: page (severity=critical)
    PD->>OC: SMS + call
    OC->>AM: ack
    OC->>M: investigate
    OC->>AM: resolve
```

**SLO tree:**
```mermaid
flowchart TB
    U["User-facing SLO\n99.9% uptime"] --> API["API availability\np99 < 500ms"]
    U --> DB["DB replication lag\n< 30s"]
    API --> Auth["Auth service\n99.95%"]
    API --> Pay["Payment service\n99.9%"]
```
