import logging
from pathlib import Path

from sqlalchemy import func, select, text

from backend.app.core.database import AsyncSessionLocal, engine
from backend.app.models import Base, Category, UserSettings
from backend.app.services.sync_service import SyncService

logger = logging.getLogger(__name__)

DEFAULT_CATEGORIES = [
    ("Oportunidad Caliente", "#ef4444"),
    ("Seguimiento", "#f59e0b"),
    ("Descartado", "#64748b"),
]

DEFAULT_FB_GROUPS = [
    {"id": "41757906864", "name": "", "enabled": True},
    {"id": "1018337428507491", "name": "", "enabled": True},
    {"id": "397742921612774", "name": "", "enabled": True},
]

MIGRATION_PGVECTOR = Path(__file__).resolve().parents[2] / "db" / "migrate_pgvector.sql"
MIGRATION_SYNC = Path(__file__).resolve().parents[2] / "db" / "migrate_sync.sql"
MIGRATION_MASS = Path(__file__).resolve().parents[2] / "db" / "migrate_mass_scrape.sql"
MIGRATION_LISTS = Path(__file__).resolve().parents[2] / "db" / "migrate_property_lists.sql"
MIGRATION_FB_GROUPS = Path(__file__).resolve().parents[2] / "db" / "migrate_fb_groups.sql"


async def _run_migration(path: Path, label: str) -> None:
    if not path.exists():
        return
    sql = path.read_text()
    async with engine.begin() as conn:
        for statement in sql.split(";"):
            stmt = statement.strip()
            if stmt:
                await conn.execute(text(stmt))
    logger.info("Migración %s aplicada", label)


async def _ensure_pgvector() -> None:
    await _run_migration(MIGRATION_PGVECTOR, "pgvector")


async def _ensure_sync() -> None:
    await _run_migration(MIGRATION_SYNC, "sync")


async def _ensure_mass_scrape() -> None:
    await _run_migration(MIGRATION_MASS, "mass_scrape")


async def _ensure_property_lists() -> None:
    await _run_migration(MIGRATION_LISTS, "property_lists")


async def _ensure_fb_groups() -> None:
    if not MIGRATION_FB_GROUPS.exists():
        return

    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'user_settings'
            AND column_name = 'facebook_groups'
            AND data_type = 'ARRAY'
        """))
        is_old_format = result.fetchone() is not None

        if is_old_format:
            logger.info("Migrando facebook_groups de TEXT[] a JSONB...")
            await conn.execute(text("ALTER TABLE user_settings ADD COLUMN facebook_groups_new JSONB"))
            await conn.execute(text("""
                UPDATE user_settings
                SET facebook_groups_new = (
                    SELECT COALESCE(jsonb_agg(
                        jsonb_build_object('id', elem, 'name', '', 'enabled', true)
                    ), '[]'::jsonb)
                    FROM unnest(facebook_groups) AS elem
                )
            """))
            await conn.execute(text("ALTER TABLE user_settings DROP COLUMN facebook_groups"))
            await conn.execute(text("ALTER TABLE user_settings DROP COLUMN IF EXISTS facebook_group_names"))
            await conn.execute(text("ALTER TABLE user_settings RENAME COLUMN facebook_groups_new TO facebook_groups"))
            await conn.execute(text("""
                ALTER TABLE user_settings ALTER COLUMN facebook_groups
                SET DEFAULT '[{"id": "41757906864", "name": "", "enabled": true},
                             {"id": "1018337428507491", "name": "", "enabled": true},
                             {"id": "397742921612774", "name": "", "enabled": true}]'::jsonb
            """))
            logger.info("Migración facebook_groups completada")
        else:
            logger.info("Migración facebook_groups no necesaria (ya está en formato JSONB)")


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await _ensure_pgvector()
    await _ensure_sync()
    await _ensure_mass_scrape()
    await _ensure_property_lists()
    await _ensure_fb_groups()

    async with AsyncSessionLocal() as session:
        category_count = await session.scalar(select(func.count()).select_from(Category))
        if not category_count:
            for name, color in DEFAULT_CATEGORIES:
                session.add(Category(name=name, color=color))
            logger.info("Seeded default categories")

        settings = await session.get(UserSettings, 1)
        if not settings:
            session.add(
                UserSettings(
                    id=1,
                    cities=["malaga"],
                    facebook_groups=DEFAULT_FB_GROUPS,
                )
            )
            logger.info("Seeded default user settings")

        await session.commit()

    async with AsyncSessionLocal() as session:
        closed = await SyncService(session).cleanup_stuck_runs()
        if closed:
            logger.warning("Cerrados %s sync runs atascados en 'running'", closed)

    logger.info("Database schema ready")
