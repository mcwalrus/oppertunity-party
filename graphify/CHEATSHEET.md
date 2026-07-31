# graphify + Claude Code cheatsheet

Repo clone: `~/.graphify/repos/Graphify-Labs/graphify` — run all commands from there.
Always pass `--backend claude-cli` (your `AWS_PROFILE` makes it auto-pick broken bedrock otherwise).

## Build

```bash
cd ~/.graphify/repos/Graphify-Labs/graphify
graphify . --backend claude-cli                          # serial (default)
GRAPHIFY_CLAUDE_CLI_PARALLEL=1 graphify . --backend claude-cli   # parallel chunks, faster
```

Output: `graphify-out/graph.json` + `GRAPH_REPORT.md` (read this first: god nodes, communities, suggested questions).

## Ask questions

```bash
graphify query "how does semantic extraction work"       # BFS subgraph answer
graphify query "..." --dfs --budget 1500                 # depth-first, smaller output
graphify explain "DigestAuth"                            # one node + neighbors, plain language
graphify path "AuthModule" "Database"                    # shortest connection between two nodes
graphify affected "Cache"                                # what breaks if X changes
graphify god-nodes --top 10                              # architectural hubs
```

(All default to `--graph graphify-out/graph.json` when run from the clone.)

## Keep it fresh

```bash
graphify update .                    # after code edits (AST only, no LLM cost)
graphify label . --backend claude-cli          # (re)name communities with LLM
graphify label . --missing-only --backend claude-cli   # name only placeholder communities
```

## Extras

```bash
graphify . --wiki                    # agent-crawlable wiki/ (pi reads this automatically)
graphify . --svg                     # graph.svg visualization
graphify . --mode deep               # richer inferred edges (more LLM spend)
graphify-mcp                         # MCP server for structured queries from pi
```

## Costs

claude-cli bills to your Claude subscription, not API credits. Serial build ≈ 17
chunks × up to 60k tokens each. `update` is free; `--mode deep` and re-labels cost more.
