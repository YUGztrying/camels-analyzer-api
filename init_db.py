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
            logger.info("Tables created successfully!")
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
