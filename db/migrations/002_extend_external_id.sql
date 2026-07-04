-- Amplía external_id para URLs largas de habitaclia
ALTER TABLE properties ALTER COLUMN external_id TYPE VARCHAR(200);
