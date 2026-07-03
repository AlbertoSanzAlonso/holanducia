import logging
from pathlib import Path

from sqlalchemy import func, select, text

from backend.app.core.database import AsyncSessionLocal, engine
from backend.app.models import Base, Category, UserSettings

logger = logging.getLogger(__name__)

DEFAULT_CATEGORIES = [
    ("Oportunidad Caliente", "#ef4444"),
    ("Seguimiento", "#f59e0b"),
    ("Descartado", "#64748b"),
]

DEFAULT_FB_GROUPS = ["41757906864", "1018337428507491", "397742921612774"]

MIGRATION_PATH = Path(__file__).resolve().parents[2] / "db" / "migrate_pgvector.sql"


async def _ensure_pgvector() -> None:
    if not MIGRATION_PATH.exists():
        return
    sql = MIGRATION_PATH.read_text()
    async with engine.begin() as conn:
        for statement in sql.split(";"):
            stmt = statement.strip()
            if stmt:
                await conn.execute(text(stmt))
    logger.info("Migración pgvector aplicada")


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await _ensure_pgvector()

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

    logger.info("Database schema ready")
