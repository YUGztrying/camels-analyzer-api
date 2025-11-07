from fastapi import FastAPI, Depends, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import BankDB
import os
import shutil
from datetime import datetime
from llm_service import extract_bank_data_from_file

app = FastAPI()


# ===== MODÈLES PYDANTIC =====

class Bank(BaseModel):
    name: str
    country: str
    total_assets: float
    currency: str = "XOF"


class BankResponse(Bank):
    id: int
    
    class Config:
        from_attributes = True


# ===== ROUTES DE BASE =====

@app.get("/")
def home():
    return {"message": "🏦 API CAMELS avec PostgreSQL !"}


# ===== ROUTES BANQUES =====

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


# ===== ROUTES UPLOAD =====

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload un fichier (PDF, CSV, image)
    Le fichier est sauvegardé dans le dossier uploads/
    """
    # Créer le dossier uploads s'il n'existe pas
    os.makedirs("uploads", exist_ok=True)
    
    # Générer un nom unique avec timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{timestamp}_{file.filename}"
    file_path = f"uploads/{unique_filename}"
    
    # Sauvegarder le fichier
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {
        "message": "Fichier uploadé avec succès !",
        "filename": file.filename,
        "saved_as": unique_filename,
        "size": f"{file.size / 1024:.2f} KB",
        "content_type": file.content_type,
        "file_url": f"/uploads/{unique_filename}"
    }


@app.get("/files")
def list_files():
    """Liste tous les fichiers uploadés"""
    if not os.path.exists("uploads"):
        return {"files": [], "total": 0}
    
    files = os.listdir("uploads")
    return {
        "total": len(files),
        "files": files
    }
@app.post("/upload-and-extract")
async def upload_and_extract(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload un fichier ET extrait automatiquement les données avec Claude.
    Puis crée la banque automatiquement !
    """
    # 1. Sauvegarder le fichier
    os.makedirs("uploads", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_filename = f"{timestamp}_{file.filename}"
    file_path = f"uploads/{unique_filename}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 2. Extraire les données avec Claude
    try:
        extracted_data = extract_bank_data_from_file(file_path)  # Au lieu de extract_bank_data_from_image
        
        # 3. Créer la banque automatiquement
        db_bank = BankDB(
            name=extracted_data.get("name", "Inconnu"),
            country=extracted_data.get("country", "Inconnu"),
            total_assets=extracted_data.get("total_assets", 0),
            currency="XOF"
        )
        db.add(db_bank)
        db.commit()
        db.refresh(db_bank)
        
        return {
            "message": "✅ Fichier uploadé, données extraites et banque créée !",
            "file": unique_filename,
            "extracted_data": extracted_data,
            "bank_created": {
                "id": db_bank.id,
                "name": db_bank.name,
                "country": db_bank.country,
                "total_assets": db_bank.total_assets
            }
        }
    
    except Exception as e:
        return {
            "message": "❌ Erreur lors de l'extraction",
            "file": unique_filename,
            "error": str(e)
        }