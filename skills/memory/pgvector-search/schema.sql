CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS memory_items_vector (
    id TEXT PRIMARY KEY,
    item_type TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT,
    embedding vector(384),
    created_at TEXT NOT NULL,
    modified_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS memory_items_vector_idx
ON memory_items_vector USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
