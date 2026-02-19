import sys
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("init_db")

MAX_RETRIES = 20
RETRY_DELAY = 5  # seconds


def _run_migrations(engine):
    """Add new columns to existing tables without dropping data (idempotent)."""
    from sqlalchemy import text

    # Columns to add to the banks table: (column_name, sql_type)
    new_columns = [
        ("npl_ratio_reported", "FLOAT"),
        ("coverage_ratio_reported", "FLOAT"),
        ("roe_reported", "FLOAT"),
        ("roa_reported", "FLOAT"),
        ("cost_income_reported", "FLOAT"),
        ("net_income_investment", "FLOAT"),
        ("other_net_income", "FLOAT"),
    ]

    with engine.connect() as conn:
        for col_name, col_type in new_columns:
            try:
                conn.execute(text(
                    f"ALTER TABLE banks ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
                ))
                conn.commit()
                logger.info(f"Migration: ensured column banks.{col_name} exists.")
            except Exception as e:
                logger.warning(f"Migration skipped for {col_name}: {e}")
                conn.rollback()

        # Relax NOT NULL on columns that IRP files don't always provide
        for col_name in ["country"]:
            try:
                conn.execute(text(
                    f"ALTER TABLE banks ALTER COLUMN {col_name} DROP NOT NULL"
                ))
                conn.commit()
                logger.info(f"Migration: relaxed NOT NULL on banks.{col_name}.")
            except Exception as e:
                logger.warning(f"Migration skipped for {col_name} nullable: {e}")
                conn.rollback()


def init_database():
    """Create database tables with retry logic for container startup."""
    logger.info("Starting database initialization...")

    from database import engine
    from models import Base
    from job_manager import JobDB  # noqa: F401 — ensures jobs table is registered

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"Attempt {attempt}/{MAX_RETRIES}: Connecting to database...")
            # Test connection
            with engine.connect() as conn:
                from sqlalchemy import text
                conn.execute(text("SELECT 1"))
            logger.info("Database connection successful.")

            logger.info("Creating/updating tables...")
            Base.metadata.create_all(bind=engine)
            logger.info("Tables created. Running column migrations...")
            _run_migrations(engine)
            logger.info("Database initialization complete!")
            return
        except Exception as e:
            logger.error(f"Attempt {attempt}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES:
                logger.info(f"Retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
            else:
                logger.error("All attempts exhausted. Could not initialize database.")
                raise RuntimeError("Database initialization failed after all retries")


if __name__ == "__main__":
    init_database()
