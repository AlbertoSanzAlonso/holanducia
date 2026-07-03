-- Migración para bases de datos existentes (idempotente)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS property_embeddings (
    id SERIAL PRIMARY KEY,
    property_id INTEGER NOT NULL UNIQUE REFERENCES properties(id) ON DELETE CASCADE,
    content_hash VARCHAR(64) NOT NULL,
    embedding vector(1536) NOT NULL,
    embedded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_property_embeddings_hnsw
    ON property_embeddings USING hnsw (embedding vector_cosine_ops);
