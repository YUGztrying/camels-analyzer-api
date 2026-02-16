from database import engine
from models import Base
from job_manager import JobDB  # noqa: F401 — ensures jobs table is registered

print("Creating/updating database tables...")
Base.metadata.create_all(bind=engine)
print("Tables created successfully!")
