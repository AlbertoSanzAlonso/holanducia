-- Sync diario: estado de anuncios y runs de reconciliación
ALTER TABLE properties ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE properties ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64);

CREATE TABLE IF NOT EXISTS sync_runs (
    id SERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status VARCHAR(50) DEFAULT 'running',
    sources TEXT[] DEFAULT ARRAY[]::TEXT[],
    stats JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_properties_active ON properties (is_active);
CREATE INDEX IF NOT EXISTS idx_properties_last_seen ON properties (last_seen_at);
CREATE INDEX IF NOT EXISTS idx_properties_source ON properties (source);
