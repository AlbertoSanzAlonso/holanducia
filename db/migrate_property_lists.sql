CREATE TABLE IF NOT EXISTS property_lists (
    id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    description TEXT,
    color VARCHAR(20) NOT NULL DEFAULT '#6366f1',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS property_list_items (
    id SERIAL PRIMARY KEY,
    list_id INTEGER NOT NULL REFERENCES property_lists(id) ON DELETE CASCADE,
    property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    note TEXT,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(list_id, property_id)
);

CREATE INDEX IF NOT EXISTS idx_property_list_items_list ON property_list_items (list_id);
CREATE INDEX IF NOT EXISTS idx_property_list_items_property ON property_list_items (property_id);
