from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import BankDB

app = FastAPI()


# Modèle Pydantic (pour l'API)
class Bank(BaseModel):
    name: str
    country: str
    total_assets: float
    currency: str = "XOF"


# Modèle de réponse (avec l'ID)
class BankResponse(Bank):
    id: int
    
    class Config:
        from_attributes = True


@app.get("/")
def home():
    return {"message": "🏦 API CAMELS avec PostgreSQL !"}


@app.post("/banks", response_model=BankResponse)
def create_bank(bank: Bank, db: Session = Depends(get_db)):
    """Crée une banque dans PostgreSQL"""
    db_bank = BankDB(**bank.model_dump())
    db.add(db_bank)
    db.commit()
    db.refresh(db_bank)
    return db_bank


@app.get("/banks")
def list_banks(db: Session = Depends(get_db)):
    """Liste toutes les banques depuis PostgreSQL"""
    banks = db.query(BankDB).all()
    return {"total": len(banks), "banks": banks}


@app.get("/banks/{bank_id}", response_model=BankResponse)
def get_bank(bank_id: int, db: Session = Depends(get_db)):
    """Récupère une banque par son ID"""
    bank = db.query(BankDB).filter(BankDB.id == bank_id).first()
    if not bank:
        return {"error": "Banque introuvable"}
    return bank