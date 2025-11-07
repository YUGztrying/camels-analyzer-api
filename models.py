from sqlalchemy import Column, Integer, String, Float
from database import Base


class BankDB(Base):
    """Modèle SQLAlchemy pour la table banks"""
    __tablename__ = "banks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    country = Column(String, nullable=False)
    total_assets = Column(Float, nullable=False)
    currency = Column(String, default="XOF")