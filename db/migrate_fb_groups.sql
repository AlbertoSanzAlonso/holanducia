-- Migrar facebook_groups de TEXT[] a JSONB con estructura {id, name, enabled}
-- Solo ejecutar si facebook_groups sigue siendo TEXT[]

DO $$
BEGIN
    -- Verificar si la columna es TEXT[] (formato antiguo)
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_settings'
        AND column_name = 'facebook_groups'
        AND data_type = 'ARRAY'
    ) THEN

        -- Crear columna nueva
        ALTER TABLE user_settings ADD COLUMN facebook_groups_new JSONB;

        -- Convertir datos existentes
        UPDATE user_settings AS u
        SET facebook_groups_new = (
            SELECT COALESCE(jsonb_agg(
                jsonb_build_object(
                    'id', elem,
                    'name', COALESCE(u.facebook_group_names->elem, '')::text,
                    'enabled', true
                )
            ), '[]'::jsonb)
            FROM unnest(u.facebook_groups) AS elem
        );

        -- Reemplazar columnas
        ALTER TABLE user_settings DROP COLUMN facebook_groups;
        ALTER TABLE user_settings DROP COLUMN facebook_group_names;
        ALTER TABLE user_settings RENAME COLUMN facebook_groups_new TO facebook_groups;

        -- Poner default
        ALTER TABLE user_settings ALTER COLUMN facebook_groups SET DEFAULT '[{"id": "41757906864", "name": "", "enabled": true}, {"id": "1018337428507491", "name": "", "enabled": true}, {"id": "397742921612774", "name": "", "enabled": true}]'::jsonb;

        RAISE NOTICE 'Migración facebook_groups completada';
    ELSE
        RAISE NOTICE 'Migración facebook_groups no necesaria (ya está en formato JSONB)';
    END IF;
END $$;
