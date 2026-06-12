-- kiro-graph schema v1
CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,          -- project, decision, task, skill, tension, artifact, agent
    name TEXT NOT NULL,
    project TEXT,                -- which project this belongs to (nullable for cross-project)
    agent TEXT,                  -- which agent created this
    status TEXT DEFAULT 'active', -- active, done, superseded, rejected, retired
    body TEXT,                   -- free-form content (markdown, JSON, etc)
    evidence TEXT,               -- JSON array of sources ["log:2026-06-09T...", "file:path"]
    created TEXT NOT NULL,
    updated TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    src TEXT NOT NULL REFERENCES entities(id),
    dst TEXT NOT NULL REFERENCES entities(id),
    rel TEXT NOT NULL,           -- owns, depends_on, blocked_by, supersedes, uses, contributed_to
    evidence TEXT,
    created TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    agent TEXT NOT NULL,
    project TEXT,
    action TEXT NOT NULL,        -- log, decide, complete, tension, link
    entity_id TEXT REFERENCES entities(id),
    msg TEXT NOT NULL
);

-- FTS for semantic-ish search over entities
CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts USING fts5(
    name, body, project, agent, type,
    content='entities', content_rowid='rowid'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS entities_ai AFTER INSERT ON entities BEGIN
    INSERT INTO entities_fts(rowid, name, body, project, agent, type)
    VALUES (new.rowid, new.name, new.body, new.project, new.agent, new.type);
END;

CREATE TRIGGER IF NOT EXISTS entities_ad AFTER DELETE ON entities BEGIN
    INSERT INTO entities_fts(entities_fts, rowid, name, body, project, agent, type)
    VALUES ('delete', old.rowid, old.name, old.body, old.project, old.agent, old.type);
END;

CREATE TRIGGER IF NOT EXISTS entities_au AFTER UPDATE ON entities BEGIN
    INSERT INTO entities_fts(entities_fts, rowid, name, body, project, agent, type)
    VALUES ('delete', old.rowid, old.name, old.body, old.project, old.agent, old.type);
    INSERT INTO entities_fts(rowid, name, body, project, agent, type)
    VALUES (new.rowid, new.name, new.body, new.project, new.agent, new.type);
END;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);
CREATE INDEX IF NOT EXISTS idx_entities_project ON entities(project);
CREATE INDEX IF NOT EXISTS idx_entities_agent ON entities(agent);
CREATE INDEX IF NOT EXISTS idx_entities_status ON entities(status);
CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst);
CREATE INDEX IF NOT EXISTS idx_edges_rel ON edges(rel);
CREATE INDEX IF NOT EXISTS idx_events_agent ON events(agent);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
