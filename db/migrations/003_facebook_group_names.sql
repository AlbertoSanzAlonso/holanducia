-- Guarda nombres de grupos Facebook (id → nombre)
ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS facebook_group_names JSONB DEFAULT '{}'::jsonb;
