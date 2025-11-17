import uuid
import threading
from datetime import datetime
from typing import Dict, Optional

jobs: Dict[str, dict] = {}

def create_job(file_path: str, filename: str) -> str:
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "id": job_id,
        "status": "processing",
        "step": "Initialisation...",
        "file_path": file_path,
        "filename": filename,
        "created_at": datetime.now().isoformat(),
        "result": None,
        "error": None
    }
    return job_id

def get_job(job_id: str) -> Optional[dict]:
    return jobs.get(job_id)

def update_job(job_id: str, status: str, step: str = None, result=None, error=None):
    if job_id in jobs:
        jobs[job_id]["status"] = status
        if step:
            jobs[job_id]["step"] = step
        if result:
            jobs[job_id]["result"] = result
        if error:
            jobs[job_id]["error"] = error
        jobs[job_id]["updated_at"] = datetime.now().isoformat()

def process_job_async(job_id: str, file_path: str):
    from llm_service import extract_bank_data_from_file
    from camels_calculator import calculate_all_ratios, rate_capital, rate_asset_quality, rate_earnings, rate_liquidity, get_composite_rating
    from models import BankDB
    from database import SessionLocal
    
    try:
        # Etape 1: Extraction
        update_job(job_id, "processing", step="Extraction du document PDF...")
        extracted_data = extract_bank_data_from_file(file_path)
        
        # Etape 2: Creer objet BankDB
        update_job(job_id, "processing", step="Preparation des donnees...")
        db = SessionLocal()
        
        bank = BankDB(
            bank_name=extracted_data.get("name", "Inconnu"),
            country=extracted_data.get("country", "Inconnu"),
            fiscal_year=extracted_data.get("fiscal_year"),
            currency=extracted_data.get("currency", "XOF"),
            file_urls=file_path,
            total_assets=extracted_data.get("total_assets", 0),
            cash_reserves_requirements=extracted_data.get("cash_reserves_requirements"),
            due_from_banks=extracted_data.get("due_from_banks"),
            investment_securities=extracted_data.get("investment_securities"),
            gross_loans=extracted_data.get("gross_loans"),
            loan_loss_provisions=extracted_data.get("loan_loss_provisions"),
            foreclosed_assets=extracted_data.get("foreclosed_assets"),
            investment_in_subs_affiliates=extracted_data.get("investment_in_subs_affiliates"),
            other_assets=extracted_data.get("other_assets"),
            fixed_assets=extracted_data.get("fixed_assets"),
            deposits=extracted_data.get("deposits"),
            interbank_liabilities=extracted_data.get("interbank_liabilities"),
            other_liabilities=extracted_data.get("other_liabilities"),
            total_liabilities=extracted_data.get("total_liabilities"),
            paid_in_capital=extracted_data.get("paid_in_capital"),
            reserves=extracted_data.get("reserves"),
            retained_earnings=extracted_data.get("retained_earnings"),
            net_profit=extracted_data.get("net_profit"),
            total_equity=extracted_data.get("total_equity"),
            interest_income=extracted_data.get("interest_income"),
            interest_expenses=extracted_data.get("interest_expenses"),
            net_interest_income=extracted_data.get("net_interest_income"),
            non_interest_income_commissions=extracted_data.get("non_interest_income_commissions"),
            net_income_investment=extracted_data.get("net_income_investment"),
            other_net_income=extracted_data.get("other_net_income"),
            operating_expenses=extracted_data.get("operating_expenses"),
            operating_profit=extracted_data.get("operating_profit"),
            provision_expenses=extracted_data.get("provision_expenses"),
            non_operating_profit_loss=extracted_data.get("non_operating_profit_loss"),
            income_tax=extracted_data.get("income_tax"),
            net_income=extracted_data.get("net_income"),
            car_regulatory=extracted_data.get("car_regulatory"),
            car_bank_reported=extracted_data.get("car_bank_reported"),
            problem_assets_mn=extracted_data.get("problem_assets_mn"),
            npls_mn=extracted_data.get("npls_mn"),
            llr_mn=extracted_data.get("llr_mn"),
            fx_rate_period_end=extracted_data.get("fx_rate_period_end"),
            fx_rate_period_avg=extracted_data.get("fx_rate_period_avg")
        )
        if extracted_data.get("npl_ratio_reported"):
            bank.npl_ratio_reported = extracted_data.get("npl_ratio_reported") / 100
        if extracted_data.get("coverage_ratio_reported"):
            bank.coverage_ratio_reported = extracted_data.get("coverage_ratio_reported") / 100
        if extracted_data.get("roe_reported"):
            bank.roe_reported = extracted_data.get("roe_reported") / 100
        if extracted_data.get("roa_reported"):
            bank.roa_reported = extracted_data.get("roa_reported") / 100
        if extracted_data.get("cost_income_reported"):
            bank.cost_income_reported = extracted_data.get("cost_income_reported") / 100
        # Etape 3: Calculer ratios
        update_job(job_id, "processing", step="Calcul des ratios CAMELS...")
        bank = calculate_all_ratios(bank)
        
        # Etape 4: Sauvegarder
        update_job(job_id, "processing", step="Sauvegarde en base de donnees...")
        db.add(bank)
        db.commit()
        db.refresh(bank)
        
        # Etape 5: Generer ratings
        ratings = {
            "capital": rate_capital(bank),
            "asset_quality": rate_asset_quality(bank),
            "earnings": rate_earnings(bank),
            "liquidity": rate_liquidity(bank)
        }
        composite = get_composite_rating(ratings["capital"], ratings["asset_quality"], ratings["earnings"], ratings["liquidity"])
        
        bank_dict = {k: v for k, v in bank.__dict__.items() if not k.startswith('_')}
        db.close()
        
        result = {
            "message": "Analyse complete terminee!",
            "file": extracted_data.get("name", "Document"),
            "bank": bank_dict,
            "camels_rating": composite,
            "detailed_ratings": ratings,
            "key_metrics": {
                "total_assets": bank.total_assets,
                "car": bank.car_regulatory,
                "roae": bank.roae,
                "roaa": bank.roaa,
                "npl_ratio": bank.npl_ratio,
                "loans_deposits": bank.gross_loans_deposits
            }
        }
        
        update_job(job_id, "completed", step="Termine!", result=result)
        
    except Exception as e:
        print(f"ERREUR JOB {job_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        update_job(job_id, "failed", step="Echec", error=str(e))