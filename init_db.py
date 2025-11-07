# Script pour créer les tables dans PostgreSQL
from database import engine
from models import Base

print("🔨 Création des tables...")
Base.metadata.create_all(bind=engine)
print("✅ Tables créées avec succès !")