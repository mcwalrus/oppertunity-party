# Audience Examples by Diagram Type

Ready-to-adapt Mermaid snippets for SWE, DevOps, and Platform Engineering.
`P` = Primary use · `S` = Secondary · `R` = Rare

---

## Flowchart — SWE P · DevOps P · Platform P

**[SWE] API endpoint routing logic**
```mermaid
flowchart LR
    REQ[/POST /users/] --> AUTH{authenticated?}
    AUTH -->|no| REJ[401]
    AUTH -->|yes| ROLE{role?}
    ROLE -->|admin| A[create admin user]
    ROLE -->|user| U[create user]
    ROLE -->|guest| G[403 forbidden]
```

**[DevOps] Deployment pipeline with gates**
```mermaid
flowchart LR
    P[push] --> CI[CI build]
    CI -->|pass| T[tests]
    CI -->|fail| FIX[notify author]
    T -->|pass| CD[CD stage]
    T -->|fail| FIX
    CD --> CAN[canary 5%]
    CAN -->|healthy| FULL[100% rollout]
    CAN -->|errors| RB[auto-rollback]
```

**[Platform] Tenant routing / multi-tenant dispatch**
```mermaid
flowchart TB
    REQ[incoming request] --> AUTH{auth ok?}
    AUTH -->|no| REJ[reject 401]
    AUTH -->|yes| TID[extract tenant_id]
    TID --> TIER{tenant tier?}
    TIER -->|free| SHARED[shared pool]
    TIER -->|paid| DEDICATED[dedicated pool]
    TIER -->|enterprise| ISOLATED[isolated cluster]
```

**[Platform] Feature-flag evaluation tree**
```mermaid
flowchart TB
    EVAL[evaluate flag] --> ENV{env match?}
    ENV -->|no| DEFAULT[return default]
    ENV -->|yes| USER[check user allowlist]
    USER -->|match| ON[return true]
    USER -->|no match| PCT{in rollout %?}
    PCT -->|yes| ON
    PCT -->|no| OFF[return false]
```

---

## Sequence — SWE P · DevOps P · Platform S

**[SWE] Method call order within a service**
```mermaid
sequenceDiagram
    participant C as Controller
    participant S as Service
    participant R as Repository
    C->>S: create(input)
    S->>S: validate
    S->>R: save(entity)
    R-->>S: ok
    S->>S: publish event
    S-->>C: result
```

**[SWE] Async webhook fan-out**
```mermaid
sequenceDiagram
    participant A as API
    participant Q as Queue
    participant W1 as Worker 1
    participant W2 as Worker 2
    A->>Q: enqueue
    par
        Q->>W1: dispatch
        W1-->>Q: done
    and
        Q->>W2: dispatch
        W2-->>Q: done
    end
```

**[DevOps] Distributed request trace with slow DB**
```mermaid
sequenceDiagram
    participant U as User
    participant CDN
    participant API as Gateway
    participant Svc as Service
    participant DB
    U->>CDN: GET /page
    CDN->>API: forward
    API->>Svc: POST /charge
    Svc->>DB: INSERT
    Note over DB: 1200ms ⚠
    DB-->>Svc: row
    Svc-->>API: 201
    API-->>CDN: 201
    CDN-->>U: 201
```

**[Platform] Auth flow across services**
```mermaid
sequenceDiagram
    participant U as User
    participant IdP as Identity Provider
    participant API as API Gateway
    participant Svc as Service
    U->>API: request + bearer token
    API->>IdP: validate token
    IdP-->>API: claims (user_id, tenant_id)
    API->>Svc: forward with claims
    Svc-->>API: response
    API-->>U: response
```

---

## State — SWE P · DevOps P · Platform S

**[SWE] Async job states**
```mermaid
stateDiagram-v2
    [*] --> Queued
    Queued --> Running: worker picks up
    Running --> Completed: success
    Running --> Failed: exception
    Failed --> Queued: retry
    Failed --> DeadLetter: max retries
    Completed --> [*]
    DeadLetter --> [*]
```

**[DevOps] Deployment rollout states**
```mermaid
stateDiagram-v2
    [*] --> Pending
    Pending --> Canary: deploy 5%
    Canary --> Healthy: metrics green
    Canary --> RolledBack: errors spike
    Healthy --> Full: promote to 100%
    Healthy --> Paused: hold for review
    RolledBack --> [*]
    Full --> [*]
```

**[Platform] Tenant lifecycle**
```mermaid
stateDiagram-v2
    [*] --> Provisioning
    Provisioning --> Active: signup complete
    Active --> Suspended: payment failed
    Suspended --> Active: payment cleared
    Active --> Deprovisioning: cancellation
    Deprovisioning --> [*]
```

---

## Architecture — SWE R · DevOps P · Platform P

**[DevOps] Three-tier web app on AWS**
```mermaid
architecture-beta
    group public(cloud)[Public]
    service cdn(internet)[CDN]
    service route(internet)[Route53]
    group app(server)[Application]
    service web(server)[Web]
    service api(server)[API]
    service db(database)[RDS]
    route --> cdn
    cdn --> web
    web --> api
    api --> db
```

**[Platform] Multi-region topology**
```mermaid
architecture-beta
    group us(cloud)[US Region]
    service usweb(server)[Web US]
    service usapi(server)[API US]
    service usdb(database)[DB US]
    group eu(cloud)[EU Region]
    service euweb(server)[Web EU]
    service euapi(server)[API EU]
    service eudb(database)[DB EU]
    usweb --> usapi
    usapi --> usdb
    euweb --> euapi
    euapi --> eudb
    usapi <-.-> euapi : replication
```

---

## C4 — SWE P · DevOps P · Platform P

**[SWE] System context (C4Context)**
```mermaid
C4Context
    title System context
    Person(author, "Author", "Creates content")
    System(blog, "Blog Platform", "Hosts posts")
    System_Ext(cdn, "CDN", "Caches content")
    Rel(author, blog, "Writes posts in")
    Rel(blog, cdn, "Serves via")
```

**[DevOps] Container view (C4Container)**
```mermaid
C4Container
    title Container view
    Person(user, "User")
    System(webapp, "Web App", "React SPA")
    System(api, "API", "Node.js")
    System(db, "Database", "Postgres")
    Rel(user, webapp, "Uses", "HTTPS")
    Rel(webapp, api, "Calls", "REST")
    Rel(api, db, "Reads/writes", "SQL")
```

---

## Gantt — SWE S · DevOps P · Platform P

**[DevOps] Maintenance window**
```mermaid
gantt
    title DB upgrade window
    dateFormat HH:mm
    axisFormat %H:%M
    section Prep
    Snapshot     :done, snap, 02:00, 10m
    section Upgrade
    Apply        :crit, apply, 02:10, 30m
    Verify       :active, verify, 02:40, 15m
    section Cutover
    Failover     :crit, fo, 02:55, 5m
    Monitor      :done, mon, 03:00, 60m
```

**[Platform] Q3 roadmap**
```mermaid
gantt
    title Q3 platform roadmap
    dateFormat YYYY-MM-DD
    section Foundations
    Auth v2      :done, auth, 2026-07-01, 14d
    Multi-region :active, mr, after auth, 21d
    section Capabilities
    Storage v3   :s3, after mr, 14d
    Compute v3   :c3, after s3, 14d
```

---

## Gitgraph — SWE P · DevOps P · Platform P

**[DevOps] Hotfix off release branch**
```mermaid
gitGraph
    commit
    commit tag: "v1.0"
    branch hotfix
    checkout hotfix
    commit
    commit tag: "v1.0.1"
    checkout main
    merge hotfix tag: "v1.0.1"
    commit
```

**[Platform] SDK versioning with parallel majors**
```mermaid
gitGraph
    commit tag: "v1.0"
    branch v2
    checkout v2
    commit
    commit tag: "v2.0"
    checkout main
    commit
    merge v2
    commit tag: "v3.0"
```

---

## XY Chart — SWE S · DevOps P · Platform P

**[DevOps] p99 latency over 24 hours**
```mermaid
xychart-beta
    title "p99 latency (ms)"
    x-axis [00, 04, 08, 12, 16, 20, 24]
    y-axis "ms" 0 --> 2000
    line [180, 190, 220, 480, 1850, 240, 195]
```

**[DevOps] Error rate by service**
```mermaid
xychart-beta
    title "Error rate (%)"
    x-axis [api, web, auth, pay, db]
    y-axis "%" 0 --> 5
    bar [0.4, 0.1, 0.2, 1.8, 0.3]
```

**[Platform] Tenant growth over 12 months**
```mermaid
xychart-beta
    title "Active tenants"
    x-axis [Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec]
    y-axis "Tenants" 0 --> 500
    bar [120, 145, 180, 210, 240, 280, 310, 340, 380, 410, 450, 480]
```

---

## Sankey — SWE S · DevOps P · Platform P

**[DevOps] Cloud cost attribution**
```mermaid
sankey-beta
    Compute,API,1200
    Compute,Web,800
    Compute,Workers,400
    Storage,DB,600
    Storage,Cache,200
    Network,CDN,300
```

**[Platform] Resource distribution across tenants**
```mermaid
sankey-beta
    Pool,Acme,400
    Pool,Beta,250
    Pool,Gamma,150
    Pool,Delta,100
    Pool,Free,100
    Acme,Compute,250
    Acme,Storage,150
    Beta,Compute,180
    Beta,Storage,70
```

---

## Radar — SWE S · DevOps P · Platform P (v11.6.0+)

**[SWE] Code quality across services**
```mermaid
radar-beta
    axis Coverage, Complexity, Duplication, Coupling, TestSpeed
    curve auth { 85, 30, 12, 20, 90 }
    curve pay  { 70, 55, 25, 45, 60 }
    curve web  { 60, 40, 30, 50, 75 }
```

**[Platform] Platform capability coverage (today vs target)**
```mermaid
radar-beta
    axis Auth, Storage, Compute, Network, Observability, Compliance
    curve today  { 80, 90, 70, 60, 85, 75 }
    curve target { 95, 95, 90, 90, 95, 95 }
```

---

## Quadrant — SWE S · DevOps P · Platform P

**[SWE] Tech debt backlog (impact vs effort)**
```mermaid
quadrantChart
    title Tech debt backlog
    x-axis Low effort --> High effort
    y-axis Low impact --> High impact
    quadrant-1 Quick wins
    quadrant-2 Strategic
    quadrant-3 Ignore
    quadrant-4 Reconsider
    AuthRefactor:   [0.2, 0.8]
    DBMigration:    [0.7, 0.9]
    LoggingCleanup: [0.3, 0.3]
    DocUpdate:      [0.8, 0.2]
```

**[DevOps] Service health (latency vs error rate)**
```mermaid
quadrantChart
    title Service health
    x-axis Low latency --> High latency
    y-axis Low errors --> High errors
    quadrant-1 Critical
    quadrant-2 Slow but stable
    quadrant-3 Healthy
    quadrant-4 Fast but flaky
    api:   [0.7, 0.8]
    auth:  [0.3, 0.2]
    db:    [0.9, 0.4]
    cache: [0.2, 0.1]
```

---

## Mindmap — SWE P · DevOps S · Platform P

**[Platform] Platform capabilities map**
```mermaid
mindmap
    root((Platform))
        Storage
          Object
          Block
          DB
        Compute
          Containers
          Functions
          VMs
        Network
          VPC
          CDN
          DNS
        Observability
          Metrics
          Traces
          Logs
```

**[DevOps] Incident investigation tree**
```mermaid
mindmap
    root((Latency spike))
        Code
          Recent deploy
          Profile
        Infra
          DB
          Cache
          Network
        Data
          Volume
          Query plan
```

---

## ER — SWE P · DevOps S · Platform S

**[SWE] E-commerce schema**
```mermaid
erDiagram
    USER ||--o{ ORDER : places
    ORDER ||--|{ LINE_ITEM : contains
    PRODUCT ||--o{ LINE_ITEM : appears_in
    USER {
        uuid id PK
        string email UK
    }
    ORDER {
        uuid id PK
        uuid user_id FK
        timestamp created_at
    }
```

**[Platform] Tenant data isolation model**
```mermaid
erDiagram
    TENANT ||--o{ TENANT_USER : has
    TENANT ||--|{ TENANT_DATA : owns
    TENANT_USER {
        uuid tenant_id FK
        uuid user_id FK
        string role
    }
    TENANT_DATA {
        uuid id PK
        uuid tenant_id FK
        jsonb payload
    }
```

---

## Requirement — SWE R · DevOps S · Platform P

**[Platform] SLA definition**
```mermaid
requirementDiagram
    requirement api_sla {
        id: 1
        text: 99.9% uptime monthly
        risk: high
        verifyMethod: measurement
    }
    functionalRequirement response_time {
        id: 2
        text: p99 < 500ms
    }
    api_sla - contains -> response_time
```

---

## Common doc × diagram combos

| Doc type | Diagram set |
|----------|-------------|
| PR description | flowchart (ownership) + sequence (hot path) + stateDiagram (lifecycle) |
| ADR / RFC | C4Context + flowchart before/after + migration path |
| Incident review | gantt (timeline) + sequence (trace) + flowchart (mitigation) |
| Runbook | flowchart (decision tree) + sequence (commands) + kanban (status) |
| SLO doc | flowchart (SLO tree) + xychart (history) + radar (multi-SLO) |
| Platform RFC | C4Container + architecture-beta + sankey (cost/resource) |
| Capacity plan | xychart (trend) + gantt (roadmap) + quadrant (priority) |
| Onboarding doc | mindmap (capabilities) + C4Context + sequence (auth flow) |
| Roadmap | timeline (milestones) + gantt (phased) + kanban (in-flight) |
