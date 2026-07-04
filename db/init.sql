CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    color VARCHAR(20) NOT NULL DEFAULT '#00acee'
);

CREATE TABLE properties (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(64),
    url VARCHAR(500) NOT NULL UNIQUE,
    source VARCHAR(100),
    title VARCHAR(500),
    price DOUBLE PRECISION DEFAULT 0,
    city VARCHAR(100),
    neighborhood VARCHAR(100),
    address VARCHAR(300),
    size_m2 DOUBLE PRECISION,
    rooms INTEGER,
    bathrooms INTEGER,
    has_parking BOOLEAN DEFAULT FALSE,
    has_terrace BOOLEAN DEFAULT FALSE,
    has_pool BOOLEAN DEFAULT FALSE,
    has_garden BOOLEAN DEFAULT FALSE,
    has_trastero BOOLEAN DEFAULT FALSE,
    garage_spots INTEGER,
    floor INTEGER,
    is_individual BOOLEAN DEFAULT FALSE,
    is_agency BOOLEAN DEFAULT TRUE,
    description TEXT,
    images JSONB DEFAULT '[]'::jsonb,
    opportunity_score INTEGER DEFAULT 0,
    opportunity_reasons JSONB DEFAULT '[]'::jsonb,
    category_id INTEGER REFERENCES categories(id),
    catastro_ref VARCHAR(100),
    year_built INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    content_hash VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sync_runs (
    id SERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status VARCHAR(50) DEFAULT 'running',
    sources TEXT[] DEFAULT ARRAY[]::TEXT[],
    stats JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE user_settings (
    id INTEGER PRIMARY KEY DEFAULT 1,
    cities TEXT[] DEFAULT ARRAY['malaga'],
    max_price INTEGER DEFAULT 300000,
    min_rooms INTEGER DEFAULT 2,
    min_size_m2 INTEGER DEFAULT 60,
    portals VARCHAR(200) DEFAULT 'Fotocasa, Habitaclia, Pisos.com, Facebook',
    max_leads_per_portal INTEGER DEFAULT 10,
    mass_scrape_target INTEGER DEFAULT 500,
    mass_fb_scroll_steps INTEGER DEFAULT 100,
    target_leads INTEGER DEFAULT 10,
    facebook_groups TEXT[] DEFAULT ARRAY['41757906864', '1018337428507491', '397742921612774'],
    portal_urls TEXT[] DEFAULT ARRAY[]::TEXT[],
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT single_settings_row CHECK (id = 1)
);

CREATE TABLE scraping_requests (
    id SERIAL PRIMARY KEY,
    status VARCHAR(50) DEFAULT 'pending',
    requested_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    source_name VARCHAR(100),
    error_message TEXT,
    target_leads INTEGER,
    groups TEXT[],
    portal_urls TEXT[]
);

INSERT INTO categories (name, color) VALUES
    ('Oportunidad Caliente', '#ef4444'),
    ('Seguimiento', '#f59e0b'),
    ('Descartado', '#64748b');

INSERT INTO user_settings (id) VALUES (1);

CREATE TABLE property_embeddings (
    id SERIAL PRIMARY KEY,
    property_id INTEGER NOT NULL UNIQUE REFERENCES properties(id) ON DELETE CASCADE,
    content_hash VARCHAR(64) NOT NULL,
    embedding vector(1536) NOT NULL,
    embedded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_property_embeddings_hnsw
    ON property_embeddings USING hnsw (embedding vector_cosine_ops);

CREATE INDEX idx_properties_created_at ON properties (created_at DESC);
CREATE INDEX idx_properties_opportunity_score ON properties (opportunity_score DESC);
CREATE INDEX idx_scraping_requests_status ON scraping_requests (status, requested_at DESC);

CREATE TABLE property_lists (
    id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    description TEXT,
    color VARCHAR(20) NOT NULL DEFAULT '#6366f1',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE property_list_items (
    id SERIAL PRIMARY KEY,
    list_id INTEGER NOT NULL REFERENCES property_lists(id) ON DELETE CASCADE,
    property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    note TEXT,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(list_id, property_id)
);

CREATE INDEX idx_property_list_items_list ON property_list_items (list_id);
CREATE INDEX idx_property_list_items_property ON property_list_items (property_id);
