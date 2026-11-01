# Graph-memory integration (T12)

bharat-arp (collections control tower) can pull codebase context from
`codebase-memory-mcp` to ground its evidence ledger and decision explanations.

## Usage

```python
from codebase_memory_mcp.repoindex import index_repo
from codebase_memory_mcp.graph import GitNexusGraph
from codebase_memory_mcp.wiring import inject_context

g = GitNexusGraph()
g.load(index_repo("/path/to/repo"))
context_block = inject_context(g, "*", "your query here")
```

## MCP (stdio)

```bash
python -m codebase_memory_mcp.mcp_server /path/to/repo
```

## Status
Adapter (M1) shipped in codebase-memory-mcp. Per-repo wiring is the remaining
slice (T12 M2).
EOF