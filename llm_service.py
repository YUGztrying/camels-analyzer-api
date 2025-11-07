# llm_service.py
import anthropic
import os
from dotenv import load_dotenv
import base64
import json
from PyPDF2 import PdfReader

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def extract_bank_data_from_file(file_path: str) -> dict:
    """
    Extrait TOUTES les données financières CAMELS d'un fichier.
    """
    
    # PROMPT AMÉLIORÉ - Extrait TOUS les champs
    prompt = """
Tu es un expert en analyse financière bancaire. Extrais TOUTES les informations suivantes d'un état financier bancaire.

INSTRUCTIONS CRITIQUES:
1. Extrais les valeurs dans leur unité d'origine (millions, milliards, etc.)
2. Pour les pourcentages (ex: CAR 11.5%), extrais comme NOMBRE (11.5)
3. Si une information est manquante, mets null
4. Sois précis et exhaustif

INFORMATIONS À EXTRAIRE:

**IDENTIFIANTS:**
- fiscal_year: Année fiscale exacte (ex: "2023", "FY23")

**BILAN - ACTIFS (en millions):**
- cash_reserves_requirements: Réserves en cash
- due_from_banks: Dû par les banques
- investment_securities: Titres d'investissement
- gross_loans: Prêts bruts TOTAL
- loan_loss_provisions: Provisions pour pertes
- foreclosed_assets: Actifs saisis
- investment_in_subs_affiliates: Investissements dans filiales
- other_assets: Autres actifs
- fixed_assets: Immobilisations
- total_assets: TOTAL ACTIFS (OBLIGATOIRE)

**BILAN - PASSIFS (en millions):**
- deposits: Dépôts clients
- interbank_liabilities: Dettes interbancaires
- other_liabilities: Autres passifs
- total_liabilities: TOTAL PASSIFS

**BILAN - CAPITAUX PROPRES (en millions):**
- paid_in_capital: Capital libéré
- reserves: Réserves
- retained_earnings: Bénéfices non distribués
- net_profit: Bénéfice net de l'exercice
- total_equity: TOTAL CAPITAUX PROPRES

**COMPTE DE RÉSULTAT (en millions):**
- interest_income: Produits d'intérêts
- interest_expenses: Charges d'intérêts
- net_interest_income: Marge nette d'intérêt
- non_interest_income_commissions: Commissions
- net_income_investment: Revenus des investissements
- other_net_income: Autres revenus nets
- operating_expenses: Frais d'exploitation
- operating_profit: Résultat d'exploitation
- provision_expenses: Dotations aux provisions
- non_operating_profit_loss: Résultat non opérationnel
- income_tax: Impôts
- net_income: RÉSULTAT NET (OBLIGATOIRE)

**RATIOS CAMELS - CAPITAL:**
- car_regulatory: CAR réglementaire (NOMBRE, ex: 11.5)
- car_bank_reported: CAR reporté par la banque (NOMBRE)

**QUALITÉ DES ACTIFS (en millions):**
- problem_assets_mn: Actifs problématiques totaux
- npls_mn: Prêts non performants (NPL)
- llr_mn: Réserves pour pertes (LLR)

**AUTRES:**
- fx_rate_period_end: Taux de change fin de période (si applicable)
- fx_rate_period_avg: Taux de change moyen (si applicable)

Réponds UNIQUEMENT en JSON avec ce format exact:
{
    "name": "Nom de la banque",
    "country": "Pays",
    "fiscal_year": "2023",
    "total_assets": 1234567,
    "cash_reserves_requirements": 123456,
    "gross_loans": 987654,
    "total_equity": 123456,
    "net_income": 12345,
    "car_regulatory": 11.5,
    "car_bank_reported": 12.8,
    "npls_mn": 8765,
    ...
}

Ne mets AUCUN texte avant ou après le JSON.
"""
    
    # Extraction selon le type de fichier
    if file_path.lower().endswith('.pdf'):
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        
        message = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=2048,  # Augmenté pour plus de données
            messages=[
                {
                    "role": "user",
                    "content": f"{prompt}\n\nVoici le contenu du document:\n\n{text[:15000]}"
                }
            ]
        )
    else:
        # Pour les images
        with open(file_path, "rb") as f:
            file_data = base64.standard_b64encode(f.read()).decode("utf-8")
        
        if file_path.lower().endswith('.png'):
            media_type = "image/png"
        elif file_path.lower().endswith('.gif'):
            media_type = "image/gif"
        elif file_path.lower().endswith('.webp'):
            media_type = "image/webp"
        else:
            media_type = "image/jpeg"
        
        message = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": file_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ],
                }
            ]
        )
    
    # Parser la réponse
    response_text = message.content[0].text
    
    # Extraire le JSON
    if "```json" in response_text:
        json_str = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        json_str = response_text.split("```")[1].split("```")[0].strip()
    else:
        json_str = response_text.strip()
    
    extracted_data = json.loads(json_str)
    
    return extracted_data