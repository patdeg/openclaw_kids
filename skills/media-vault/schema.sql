-- Media Vault Schema
-- Location: ~/clawd/vault/vault.db

-- Main media items table
CREATE TABLE IF NOT EXISTS media_items (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL CHECK (type IN ('image', 'audio', 'document')),
    topic TEXT NOT NULL,

    original_filename TEXT NOT NULL,
    stored_filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    mime_type TEXT,

    description TEXT,
    tags TEXT,

    content_text TEXT,
    content_json TEXT,

    source TEXT DEFAULT 'assistant',
    session_id TEXT,
    duration_seconds INTEGER,

    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at TEXT
);

-- Full-text search index
CREATE VIRTUAL TABLE IF NOT EXISTS media_fts USING fts5(
    id,
    topic,
    description,
    tags,
    content_text,
    content='media_items',
    content_rowid='rowid'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS media_ai AFTER INSERT ON media_items BEGIN
    INSERT INTO media_fts(rowid, id, topic, description, tags, content_text)
    VALUES (NEW.rowid, NEW.id, NEW.topic, NEW.description, NEW.tags, NEW.content_text);
END;

CREATE TRIGGER IF NOT EXISTS media_ad AFTER DELETE ON media_items BEGIN
    INSERT INTO media_fts(media_fts, rowid, id, topic, description, tags, content_text)
    VALUES('delete', OLD.rowid, OLD.id, OLD.topic, OLD.description, OLD.tags, OLD.content_text);
END;

CREATE TRIGGER IF NOT EXISTS media_au AFTER UPDATE ON media_items BEGIN
    INSERT INTO media_fts(media_fts, rowid, id, topic, description, tags, content_text)
    VALUES('delete', OLD.rowid, OLD.id, OLD.topic, OLD.description, OLD.tags, OLD.content_text);
    INSERT INTO media_fts(rowid, id, topic, description, tags, content_text)
    VALUES (NEW.rowid, NEW.id, NEW.topic, NEW.description, NEW.tags, NEW.content_text);
END;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_media_type ON media_items(type);
CREATE INDEX IF NOT EXISTS idx_media_topic ON media_items(topic);
CREATE INDEX IF NOT EXISTS idx_media_created ON media_items(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_media_deleted ON media_items(deleted_at);
