"""kiro-graph: MCP knowledge graph server for multi-agent coordination."""
import json, sqlite3, uuid, sys, os
from datetime import datetime, timezone
from pathlib import Path
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

DB_PATH = Path(os.environ.get("KIRO_GRAPH_DB", Path.home() / "kiro-graph" / "graph.db"))
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

VALID_CATEGORIES = [
    "data-format", "api-integration", "build-deploy", "logic-bug",
    "performance", "config", "git-workflow", "loop-control", "review-pattern"
]

def get_db() -> sqlite3.Connection:
    db = sqlite3.connect(str(DB_PATH), timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=5000")
    return db

def migrate_db(db: sqlite3.Connection):
    """Migrate from v1 to v2 if needed."""
    cols = {row[1] for row in db.execute("PRAGMA table_info(entities)").fetchall()}
    if "category" not in cols:
        db.execute("ALTER TABLE entities ADD COLUMN category TEXT")
        db.execute("ALTER TABLE entities ADD COLUMN q_value REAL DEFAULT 0.5")
        db.execute("ALTER TABLE entities ADD COLUMN use_count INTEGER DEFAULT 0")
        db.execute("CREATE INDEX IF NOT EXISTS idx_entities_category ON entities(category)")
        # Rebuild FTS to include category
        db.execute("DROP TABLE IF EXISTS entities_fts")
        db.execute("DROP TRIGGER IF EXISTS entities_ai")
        db.execute("DROP TRIGGER IF EXISTS entities_ad")
        db.execute("DROP TRIGGER IF EXISTS entities_au")
        db.executescript("""
            CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts USING fts5(
                name, body, project, agent, type, category,
                content='entities', content_rowid='rowid'
            );
            CREATE TRIGGER IF NOT EXISTS entities_ai AFTER INSERT ON entities BEGIN
                INSERT INTO entities_fts(rowid, name, body, project, agent, type, category)
                VALUES (new.rowid, new.name, new.body, new.project, new.agent, new.type, new.category);
            END;
            CREATE TRIGGER IF NOT EXISTS entities_ad AFTER DELETE ON entities BEGIN
                INSERT INTO entities_fts(entities_fts, rowid, name, body, project, agent, type, category)
                VALUES ('delete', old.rowid, old.name, old.body, old.project, old.agent, old.type, old.category);
            END;
            CREATE TRIGGER IF NOT EXISTS entities_au AFTER UPDATE ON entities BEGIN
                INSERT INTO entities_fts(entities_fts, rowid, name, body, project, agent, type, category)
                VALUES ('delete', old.rowid, old.name, old.body, old.project, old.agent, old.type, old.category);
                INSERT INTO entities_fts(rowid, name, body, project, agent, type, category)
                VALUES (new.rowid, new.name, new.body, new.project, new.agent, new.type, new.category);
            END;
        """)
        # Re-index existing entities into FTS
        rows = db.execute("SELECT rowid, name, body, project, agent, type, category FROM entities").fetchall()
        for r in rows:
            db.execute("INSERT INTO entities_fts(rowid, name, body, project, agent, type, category) VALUES (?,?,?,?,?,?,?)",
                       (r["rowid"], r["name"], r["body"], r["project"], r["agent"], r["type"], r["category"]))
        db.commit()

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = get_db()
    db.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    migrate_db(db)
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
        Tool(name="graph_learn", description="Record a categorized skill/experience for cross-agent sharing. Use after solving a non-trivial problem.", inputSchema={
            "type": "object",
            "properties": {
                "agent": {"type": "string", "description": "Your agent name"},
                "project": {"type": "string", "description": "Project where this was learned"},
                "category": {"type": "string", "enum": ["data-format", "api-integration", "build-deploy", "logic-bug", "performance", "config", "git-workflow", "loop-control", "review-pattern"], "description": "Problem category"},
                "trigger": {"type": "string", "description": "When does this problem occur? (the symptom/situation)"},
                "solution": {"type": "string", "description": "What to do (the fix/approach)"},
                "pitfalls": {"type": "string", "description": "What NOT to do / common mistakes"},
                "evidence": {"type": "array", "items": {"type": "string"}, "description": "File paths, URLs, log refs"},
            },
            "required": ["agent", "category", "trigger", "solution"]
        }),
        Tool(name="graph_recall", description="Search for skills by category and/or query. Defaults to your own project's skills. Set global=true to search all projects.", inputSchema={
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": ["data-format", "api-integration", "build-deploy", "logic-bug", "performance", "config", "git-workflow", "loop-control", "review-pattern"], "description": "Filter by problem category"},
                "query": {"type": "string", "description": "Free-text search within skills"},
                "project": {"type": "string", "description": "Filter by project (defaults to your project — acts as per-team KB)"},
                "global": {"type": "boolean", "description": "Set true to search ALL projects, not just your own. Default: false"},
                "limit": {"type": "integer", "default": 5, "description": "Max results"},
            },
            "required": []
        }),
        Tool(name="graph_reward", description="Update Q-value on a skill after using it. Call with reward=1.0 if it helped, 0.0 if misleading.", inputSchema={
            "type": "object",
            "properties": {
                "skill_id": {"type": "string", "description": "ID of the skill entity"},
                "reward": {"type": "number", "description": "0.0 (useless/wrong) to 1.0 (perfect). Learning rate alpha=0.1"},
                "agent": {"type": "string", "description": "Who used this skill"},
            },
            "required": ["skill_id", "reward"]
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

    elif name == "graph_learn":
        eid = str(uuid.uuid4())[:8]
        category = arguments["category"]
        if category not in VALID_CATEGORIES:
            return [TextContent(type="text", text=f"Invalid category: {category}. Must be one of: {', '.join(VALID_CATEGORIES)}")]
        # Build structured body
        body_parts = [f"TRIGGER: {arguments['trigger']}", f"SOLUTION: {arguments['solution']}"]
        if arguments.get("pitfalls"):
            body_parts.append(f"PITFALLS: {arguments['pitfalls']}")
        body = "\n".join(body_parts)
        # Name = "category: short trigger description"
        skill_name = f"{category}: {arguments['trigger'][:80]}"
        evidence = json.dumps(arguments.get("evidence", []))
        db.execute(
            "INSERT INTO entities (id,type,name,project,agent,status,body,evidence,category,q_value,use_count,created,updated) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (eid, "skill", skill_name, arguments.get("project"), arguments["agent"], "active", body, evidence, category, 0.5, 0, ts, ts)
        )
        db.execute("INSERT INTO events (ts, agent, project, action, entity_id, msg) VALUES (?,?,?,?,?,?)",
                   (ts, arguments["agent"], arguments.get("project"), "learn", eid, f"Learned: {skill_name}"))
        db.commit()
        return [TextContent(type="text", text=f"Skill recorded: {skill_name} (id={eid}, category={category}, Q=0.5)")]

    elif name == "graph_recall":
        category = arguments.get("category")
        query = arguments.get("query")
        project = arguments.get("project")
        is_global = arguments.get("global", False)
        limit = arguments.get("limit", 5)

        # Build project filter
        proj_clause = ""
        proj_params = []
        if not is_global and project:
            proj_clause = "AND e.project=?"
            proj_params = [project]

        if query and category:
            rows = db.execute(
                f"SELECT e.id, e.name, e.category, e.body, e.q_value, e.use_count, e.agent, e.project, e.updated "
                f"FROM entities_fts f JOIN entities e ON f.rowid = e.rowid "
                f"WHERE entities_fts MATCH ? AND e.type='skill' AND e.category=? AND e.status='active' {proj_clause} "
                f"ORDER BY e.q_value DESC LIMIT ?",
                (query, category, *proj_params, limit)
            ).fetchall()
        elif category:
            rows = db.execute(
                f"SELECT id, name, category, body, q_value, use_count, agent, project, updated "
                f"FROM entities WHERE type='skill' AND category=? AND status='active' {proj_clause.replace('e.', '')} "
                f"ORDER BY q_value DESC LIMIT ?",
                (category, *proj_params, limit)
            ).fetchall()
        elif query:
            rows = db.execute(
                f"SELECT e.id, e.name, e.category, e.body, e.q_value, e.use_count, e.agent, e.project, e.updated "
                f"FROM entities_fts f JOIN entities e ON f.rowid = e.rowid "
                f"WHERE entities_fts MATCH ? AND e.type='skill' AND e.status='active' {proj_clause} "
                f"ORDER BY e.q_value DESC LIMIT ?",
                (query, *proj_params, limit)
            ).fetchall()
        else:
            rows = db.execute(
                f"SELECT id, name, category, body, q_value, use_count, agent, project, updated "
                f"FROM entities WHERE type='skill' AND status='active' {proj_clause.replace('e.', '')} "
                f"ORDER BY q_value DESC LIMIT ?",
                (*proj_params, limit)
            ).fetchall()

        results = [dict(r) for r in rows]
        # If no results in project scope, hint about global search
        if not results and not is_global and project:
            # Auto-fallback: try global
            if query:
                rows = db.execute(
                    "SELECT e.id, e.name, e.category, e.body, e.q_value, e.use_count, e.agent, e.project, e.updated "
                    "FROM entities_fts f JOIN entities e ON f.rowid = e.rowid "
                    "WHERE entities_fts MATCH ? AND e.type='skill' AND e.status='active' "
                    "ORDER BY e.q_value DESC LIMIT ?",
                    (query, limit)
                ).fetchall()
            elif category:
                rows = db.execute(
                    "SELECT id, name, category, body, q_value, use_count, agent, project, updated "
                    "FROM entities WHERE type='skill' AND category=? AND status='active' "
                    "ORDER BY q_value DESC LIMIT ?",
                    (category, limit)
                ).fetchall()
            else:
                rows = []
            global_results = [dict(r) for r in rows]
            if global_results:
                return [TextContent(type="text", text=json.dumps({"your_project": [], "global_matches": global_results, "hint": "No skills in your project, but found matches from other teams. Use global=true to include these."}, indent=2, ensure_ascii=False))]
            return [TextContent(type="text", text="No skills found. You're on your own — record what you learn with graph_learn!")]
        if not results:
            return [TextContent(type="text", text="No skills found. You're on your own — record what you learn with graph_learn!")]
        return [TextContent(type="text", text=json.dumps(results, indent=2, ensure_ascii=False))]

    elif name == "graph_reward":
        skill_id = arguments["skill_id"]
        reward = max(0.0, min(1.0, arguments["reward"]))  # clamp [0, 1]
        alpha = 0.1  # learning rate

        row = db.execute("SELECT q_value, use_count FROM entities WHERE id=? AND type='skill'", (skill_id,)).fetchone()
        if not row:
            return [TextContent(type="text", text=f"Skill not found: {skill_id}")]

        old_q = row["q_value"] or 0.5
        new_q = round(old_q + alpha * (reward - old_q), 4)
        new_count = (row["use_count"] or 0) + 1

        db.execute("UPDATE entities SET q_value=?, use_count=?, updated=? WHERE id=?", (new_q, new_count, ts, skill_id))
        db.execute("INSERT INTO events (ts, agent, project, action, entity_id, msg) VALUES (?,?,?,?,?,?)",
                   (ts, arguments.get("agent", "unknown"), None, "reward", skill_id, f"Q: {old_q}→{new_q} (reward={reward})"))
        db.commit()
        return [TextContent(type="text", text=f"Q-value updated: {old_q} → {new_q} (reward={reward}, uses={new_count})")]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    init_db()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
