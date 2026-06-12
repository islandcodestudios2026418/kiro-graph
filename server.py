"""kiro-graph: MCP knowledge graph server for multi-agent coordination."""
import json, sqlite3, uuid, sys, os
from datetime import datetime, timezone
from pathlib import Path
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

DB_PATH = Path(os.environ.get("KIRO_GRAPH_DB", Path.home() / "kiro-graph" / "graph.db"))
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

def get_db() -> sqlite3.Connection:
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    return db

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = get_db()
    db.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    db.close()

def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

server = Server("kiro-graph")

@server.list_tools()
async def list_tools():
    return [
        Tool(name="graph_log", description="Log an event/action to the graph. Use this after any substantive action.", inputSchema={
            "type": "object",
            "properties": {
                "agent": {"type": "string", "description": "Your agent name (e.g. tw-accounting, job-search, main)"},
                "project": {"type": "string", "description": "Project name"},
                "msg": {"type": "string", "description": "What happened (brief)"},
            },
            "required": ["agent", "msg"]
        }),
        Tool(name="graph_decide", description="Record a decision with evidence and lifecycle tracking.", inputSchema={
            "type": "object",
            "properties": {
                "agent": {"type": "string"},
                "project": {"type": "string"},
                "name": {"type": "string", "description": "Decision title"},
                "body": {"type": "string", "description": "Details: what was decided, alternatives rejected, reasoning"},
                "evidence": {"type": "array", "items": {"type": "string"}, "description": "Sources: file paths, URLs, log refs"},
            },
            "required": ["agent", "name", "body"]
        }),
        Tool(name="graph_entity", description="Create or update an entity in the graph.", inputSchema={
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["project", "decision", "task", "skill", "tension", "artifact", "agent"]},
                "name": {"type": "string"},
                "project": {"type": "string"},
                "agent": {"type": "string"},
                "status": {"type": "string", "enum": ["active", "done", "superseded", "rejected", "retired"]},
                "body": {"type": "string"},
                "evidence": {"type": "array", "items": {"type": "string"}},
                "id": {"type": "string", "description": "Existing entity ID to update (omit to create new)"},
            },
            "required": ["type", "name"]
        }),
        Tool(name="graph_link", description="Create a relationship between two entities.", inputSchema={
            "type": "object",
            "properties": {
                "src": {"type": "string", "description": "Source entity ID or name"},
                "dst": {"type": "string", "description": "Destination entity ID or name"},
                "rel": {"type": "string", "enum": ["owns", "depends_on", "blocked_by", "supersedes", "uses", "contributed_to", "needs_input_from"]},
                "evidence": {"type": "string"},
            },
            "required": ["src", "dst", "rel"]
        }),
        Tool(name="graph_search", description="Search the knowledge graph by text query.", inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "type": {"type": "string", "description": "Filter by entity type"},
                "project": {"type": "string", "description": "Filter by project"},
                "agent": {"type": "string", "description": "Filter by agent"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["query"]
        }),
        Tool(name="graph_status", description="Get a global status overview of all projects, agents, and blockers.", inputSchema={
            "type": "object", "properties": {}, "required": []
        }),
        Tool(name="graph_query", description="Query entities by type, project, agent, or status.", inputSchema={
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "project": {"type": "string"},
                "agent": {"type": "string"},
                "status": {"type": "string"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": []
        }),
        Tool(name="graph_tensions", description="List unresolved tensions: deadlines, stale items, conflicts, blockers.", inputSchema={
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Filter by project (optional)"},
            },
            "required": []
        }),
    ]

def resolve_entity_id(db, ref: str) -> str | None:
    """Resolve an entity by ID or name."""
    row = db.execute("SELECT id FROM entities WHERE id=?", (ref,)).fetchone()
    if row: return row["id"]
    row = db.execute("SELECT id FROM entities WHERE name=? ORDER BY updated DESC LIMIT 1", (ref,)).fetchone()
    return row["id"] if row else None

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    db = get_db()
    ts = now()

    if name == "graph_log":
        eid = str(uuid.uuid4())[:8]
        db.execute("INSERT INTO events (ts, agent, project, action, msg) VALUES (?,?,?,?,?)",
                   (ts, arguments["agent"], arguments.get("project"), "log", arguments["msg"]))
        db.commit()
        return [TextContent(type="text", text=f"Logged: {arguments['msg']}")]

    elif name == "graph_decide":
        eid = str(uuid.uuid4())[:8]
        evidence = json.dumps(arguments.get("evidence", []))
        db.execute("INSERT INTO entities (id,type,name,project,agent,status,body,evidence,created,updated) VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (eid, "decision", arguments["name"], arguments.get("project"), arguments.get("agent"), "active", arguments["body"], evidence, ts, ts))
        db.execute("INSERT INTO events (ts, agent, project, action, entity_id, msg) VALUES (?,?,?,?,?,?)",
                   (ts, arguments.get("agent","unknown"), arguments.get("project"), "decide", eid, arguments["name"]))
        db.commit()
        return [TextContent(type="text", text=f"Decision recorded: {arguments['name']} (id={eid})")]

    elif name == "graph_entity":
        if arguments.get("id"):
            eid = arguments["id"]
            sets, vals = [], []
            for k in ("name","type","project","agent","status","body"):
                if k in arguments:
                    sets.append(f"{k}=?"); vals.append(arguments[k])
            if "evidence" in arguments:
                sets.append("evidence=?"); vals.append(json.dumps(arguments["evidence"]))
            sets.append("updated=?"); vals.append(ts)
            vals.append(eid)
            db.execute(f"UPDATE entities SET {','.join(sets)} WHERE id=?", vals)
        else:
            eid = str(uuid.uuid4())[:8]
            evidence = json.dumps(arguments.get("evidence", []))
            db.execute("INSERT INTO entities (id,type,name,project,agent,status,body,evidence,created,updated) VALUES (?,?,?,?,?,?,?,?,?,?)",
                       (eid, arguments["type"], arguments["name"], arguments.get("project"), arguments.get("agent"), arguments.get("status","active"), arguments.get("body"), evidence, ts, ts))
        db.commit()
        return [TextContent(type="text", text=f"Entity {'updated' if arguments.get('id') else 'created'}: {arguments['name']} (id={eid})")]

    elif name == "graph_link":
        src_id = resolve_entity_id(db, arguments["src"])
        dst_id = resolve_entity_id(db, arguments["dst"])
        if not src_id: return [TextContent(type="text", text=f"Source not found: {arguments['src']}")]
        if not dst_id: return [TextContent(type="text", text=f"Destination not found: {arguments['dst']}")]
        db.execute("INSERT INTO edges (src,dst,rel,evidence,created) VALUES (?,?,?,?,?)",
                   (src_id, dst_id, arguments["rel"], arguments.get("evidence"), ts))
        db.commit()
        return [TextContent(type="text", text=f"Linked: {arguments['src']} --[{arguments['rel']}]--> {arguments['dst']}")]

    elif name == "graph_search":
        q = arguments["query"]
        limit = arguments.get("limit", 10)
        where_parts, params = [], []
        if arguments.get("type"): where_parts.append("type=?"); params.append(arguments["type"])
        if arguments.get("project"): where_parts.append("project=?"); params.append(arguments["project"])
        if arguments.get("agent"): where_parts.append("agent=?"); params.append(arguments["agent"])
        # FTS search
        rows = db.execute(
            f"SELECT e.id, e.type, e.name, e.project, e.agent, e.status, e.body, e.updated "
            f"FROM entities_fts f JOIN entities e ON f.rowid = e.rowid "
            f"WHERE entities_fts MATCH ? {'AND ' + ' AND '.join(where_parts) if where_parts else ''} "
            f"ORDER BY rank LIMIT ?",
            (q, *params, limit)
        ).fetchall()
        results = [dict(r) for r in rows]
        return [TextContent(type="text", text=json.dumps(results, indent=2, ensure_ascii=False))]

    elif name == "graph_status":
        projects = db.execute("SELECT name, status, updated FROM entities WHERE type='project' ORDER BY updated DESC").fetchall()
        recent = db.execute("SELECT ts, agent, project, msg FROM events ORDER BY ts DESC LIMIT 15").fetchall()
        tensions = db.execute("SELECT name, project, body FROM entities WHERE type='tension' AND status='active'").fetchall()
        blocked = db.execute(
            "SELECT e.name, e.project FROM entities e JOIN edges g ON e.id=g.src WHERE g.rel='blocked_by' AND e.status='active'"
        ).fetchall()
        out = {
            "projects": [dict(r) for r in projects],
            "recent_events": [dict(r) for r in recent],
            "active_tensions": [dict(r) for r in tensions],
            "blocked_items": [dict(r) for r in blocked],
        }
        return [TextContent(type="text", text=json.dumps(out, indent=2, ensure_ascii=False))]

    elif name == "graph_query":
        where_parts, params = ["1=1"], []
        for k in ("type", "project", "agent", "status"):
            if arguments.get(k): where_parts.append(f"{k}=?"); params.append(arguments[k])
        limit = arguments.get("limit", 20)
        rows = db.execute(
            f"SELECT id, type, name, project, agent, status, updated FROM entities WHERE {' AND '.join(where_parts)} ORDER BY updated DESC LIMIT ?",
            (*params, limit)
        ).fetchall()
        return [TextContent(type="text", text=json.dumps([dict(r) for r in rows], indent=2, ensure_ascii=False))]

    elif name == "graph_tensions":
        where = "type='tension' AND status='active'"
        params = []
        if arguments.get("project"): where += " AND project=?"; params.append(arguments["project"])
        rows = db.execute(f"SELECT id, name, project, body, created FROM entities WHERE {where} ORDER BY created DESC", params).fetchall()
        # Also check for stale projects (no events in 3 days)
        stale = db.execute(
            "SELECT DISTINCT project FROM events GROUP BY project HAVING MAX(ts) < datetime('now', '-3 days')"
        ).fetchall()
        out = {"tensions": [dict(r) for r in rows], "stale_projects": [r["project"] for r in stale if r["project"]]}
        return [TextContent(type="text", text=json.dumps(out, indent=2, ensure_ascii=False))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    init_db()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
