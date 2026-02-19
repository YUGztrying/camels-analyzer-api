import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is required. Set it in .env")

# Railway uses postgres:// but SQLAlchemy requires postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Log masked URL for debugging (show host only)
try:
    from urllib.parse import urlparse
    parsed = urlparse(DATABASE_URL)
    logger.info(f"Database host: {parsed.hostname}:{parsed.port}, db: {parsed.path}")
except Exception:
    logger.info("Database URL configured (could not parse for logging)")

# Detect SQLite (used in tests) vs PostgreSQL
_is_sqlite = DATABASE_URL.startswith("sqlite")

engine_kwargs = {}
if not _is_sqlite:
    engine_kwargs.update(
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,  # Verify connections before use
    )
else:
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
