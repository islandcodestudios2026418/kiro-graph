# kiro-graph

MCP knowledge graph server for kiro-cli multi-agent memory and coordination.

## Setup

```bash
pip install mcp
git clone https://github.com/saitama3292-onepunch/kiro-graph.git ~/kiro-graph
```

## Agent Config

Add to your agent's JSON config (`~/.kiro/agents/your-agent.json`):

```json
"mcpServers": {
    "kiro-graph": {
        "command": "python",
        "args": ["~/kiro-graph/server.py"],
        "env": {}
    }
}
```

## Tools Provided

- `graph_log` — Log events/actions
- `graph_decide` — Record decisions with evidence
- `graph_entity` — Create/update entities (project, task, skill, tension, artifact, agent)
- `graph_link` — Create relationships between entities
- `graph_query` — Query entities by type/project/agent/status
- `graph_search` — Full-text search across the graph
- `graph_status` — Global overview of all projects
- `graph_tensions` — List unresolved blockers/deadlines

## Data

SQLite database auto-created at `~/kiro-graph/graph.db` on first run.
