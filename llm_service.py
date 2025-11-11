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
    
    prompt = """
Tu es un expert en analyse financière bancaire UEMOA/CEMAC. Extrais TOUTES les informations du bilan et compte de résultat.

INSTRUCTIONS CRITIQUES:
1. Lis le DOCUMENT ENTIER - Balance Sheet ET Income Statement
2. Cherche les valeurs sous TOUS leurs noms possibles (voir ci-dessous)
3. Extrais les CHIFFRES EXACTS dans leur unité (millions XOF, USD, etc.)
4. Pour les pourcentages: extrais le NOMBRE (11.5% → 11.5)
5. Si vraiment absent après recherche exhaustive: null

═══════════════════════════════════════════════════════════════

BILAN - ACTIFS (cherche ces noms ET leurs variantes):

cash_reserves_requirements:
→ "Cash & Reserve Requirements" / "Caisse et Banque Centrale" / "Disponibilités et réserves"

due_from_banks:
→ "Due from Banks" / "Correspondants bancaires" / "Comptes à vue auprès des établissements de crédit"

investment_securities:
→ "Investment Securities" / "Titres de placement" / "Portefeuille-titres" / "Valeurs mobilières"

gross_loans:
→ "Gross Loans" / "Crédits à la clientèle" / "Encours de crédit" / "Prêts bruts"

loan_loss_provisions:
→ "Loan Loss Provisions" / "Provisions pour créances douteuses" / "Dépréciation des créances" (VALEUR NÉGATIVE)

foreclosed_assets:
→ "Foreclosed Assets" / "Immobilisations saisies" / "Actifs repris"

other_assets:
→ "Other Assets" / "Autres actifs" / "Actifs divers"

fixed_assets:
→ "Fixed Assets" / "Immobilisations" / "Actifs immobilisés" / "Immobilisations corporelles"

total_assets:
→ "Total Assets" / "Total Actif" / "TOTAL BILAN ACTIF" (OBLIGATOIRE)

═══════════════════════════════════════════════════════════════

BILAN - PASSIFS:

deposits:
→ "Deposits" / "Dépôts de la clientèle" / "Comptes créditeurs de la clientèle"

interbank_liabilities:
→ "Interbank Liabilities" / "Dettes envers les établissements de crédit"

other_liabilities:
→ "Other Liabilities" / "Autres passifs" / "Dettes diverses"

total_liabilities:
→ "Total Liabilities" / "Total Passif" / "TOTAL DETTES"

═══════════════════════════════════════════════════════════════

BILAN - CAPITAUX PROPRES:

paid_in_capital:
→ "Paid in Capital" / "Capital social" / "Capital"

reserves:
→ "Reserves" / "Réserves" / "Réserves légales et statutaires"

retained_earnings:
→ "Retained Earnings" / "Report à nouveau" / "Bénéfices reportés"

net_profit:
→ "Net Profit" / "Résultat net de l'exercice" / "Bénéfice net"

total_equity:
→ "Total Equity" / "Capitaux propres" / "Total fonds propres" (OBLIGATOIRE)

═══════════════════════════════════════════════════════════════

COMPTE DE RÉSULTAT:

interest_income:
→ "Interest Income" / "Produits d'intérêts" / "Intérêts et produits assimilés"

interest_expenses:
→ "Interest Expenses" / "Charges d'intérêts" / "Intérêts et charges assimilées" (VALEUR POSITIVE, on inversera)

net_interest_income:
→ "Net Interest Income" / "Marge nette d'intérêt" / "Produit net bancaire d'intérêt"

non_interest_income_commissions:
→ "Non-Interest Income" / "Commissions" / "Produits de commissions" / "Commissions reçues"

net_income_investment:
→ "Net Income from Investment" / "Gains sur titres" / "Produits du portefeuille-titres"

other_net_income:
→ "Other Net Income" / "Autres produits nets" / "Produits divers"

operating_expenses:
→ "Operating Expenses" / "Frais généraux" / "Charges d'exploitation" / "Frais de personnel + autres frais"

operating_profit:
→ "Operating Profit" / "Résultat d'exploitation" / "Résultat brut d'exploitation"

provision_expenses:
→ "Provision Expenses" / "Dotations aux provisions" / "Coût du risque"

non_operating_profit_loss:
→ "Non-Operating Profit/Loss" / "Résultat exceptionnel" / "Éléments non récurrents"

income_tax:
→ "Income Tax" / "Impôts sur les bénéfices" / "Charge d'impôt"

net_income:
→ "Net Income" / "Résultat net" / "Bénéfice net de l'exercice" (OBLIGATOIRE)

═══════════════════════════════════════════════════════════════

RATIOS CAMELS:

car_regulatory:
→ "CAR" / "Ratio de solvabilité" / "Ratio Cooke" / "Ratio McDonough" (NOMBRE seulement: 11.5)

car_bank_reported:
→ "CAR banque" / "Solvabilité déclarée" (NOMBRE seulement: 14.6)

═══════════════════════════════════════════════════════════════

QUALITÉ DES ACTIFS:

npls_mn:
→ "NPLs" / "Créances en souffrance" / "Créances douteuses" / "Prêts non performants"

═══════════════════════════════════════════════════════════════

MÉTHODOLOGIE:
1. Scanne TOUT le document ligne par ligne
2. Pour chaque champ, cherche TOUTES ses variantes
3. Si tu trouves le label mais pas le chiffre: regarde la colonne de droite
4. Les chiffres peuvent être en format: "1,234.5" ou "1 234,5" ou "1234"
5. Attention aux sous-totaux vs totaux

FORMAT DE RÉPONSE (JSON UNIQUEMENT, AUCUN TEXTE):
{
    "name": "Nom de la banque",
    "fiscal_year": "2021",
    "total_assets": 1316459,
    "cash_reserves_requirements": 65797,
    "due_from_banks": null,
    "investment_securities": null,
    "gross_loans": 889832,
    "loan_loss_provisions": -25000,
    "foreclosed_assets": null,
    "other_assets": null,
    "fixed_assets": null,
    "total_liabilities": 1185660,
    "deposits": 1099658,
    "interbank_liabilities": null,
    "other_liabilities": null,
    "paid_in_capital": 10000,
    "reserves": null,
    "retained_earnings": 86768,
    "net_profit": null,
    "total_equity": 130799,
    "interest_income": 74957,
    "interest_expenses": 16362,
    "net_interest_income": 58595,
    "non_interest_income_commissions": null,
    "net_income_investment": null,
    "other_net_income": null,
    "operating_expenses": 34490,
    "operating_profit": 42042,
    "provision_expenses": null,
    "non_operating_profit_loss": null,
    "income_tax": 6697,
    "net_income": 34031,
    "car_regulatory": null,
    "car_bank_reported": null,
    "npls_mn": null
}
"""
    
    # Extraction selon le type de fichier
    if file_path.lower().endswith('.pdf'):
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        
        # Si le texte est vide ou trop court, le PDF est probablement scanné
        if len(text.strip()) < 100:
            print("⚠️ PDF scanné détecté, conversion en image...")
            from pdf2image import convert_from_path
            
            # Convertir première page en image
            images = convert_from_path(file_path, first_page=1, last_page=1)
            print(f"✅ {len(images)} page(s) convertie(s)")
            if images:
                # Sauvegarder temporairement
                temp_image = file_path.replace('.pdf', '_temp.png')
                images[0].save(temp_image, 'PNG')
                print(f"✅ Image sauvegardée: {temp_image}")
                # Envoyer comme image
                with open(temp_image, "rb") as f:
                    file_data = base64.standard_b64encode(f.read()).decode("utf-8")
                print(f"✅ Image encodée: {len(file_data)} chars")
                message = client.messages.create(
                    model="claude-3-5-haiku-20241022",
                    max_tokens=4096,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": file_data}},
                            {"type": "text", "text": prompt}
                        ]
                    }]
                )
                print("✅ Message envoyé à Claude")
                os.remove(temp_image)
                # Supprimer temp
                os.remove(temp_image)
            else:
                raise Exception("Impossible de convertir le PDF")
        else:
            # PDF avec texte extractible
            message = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": f"{prompt}\n\nDocument:\n\n{text[:50000]}"
                }]
            )
        
        # AUGMENTÉ: Envoie TOUT le texte, pas seulement 15000 chars
        message = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=4096,  # Augmenté pour plus de données
            messages=[
                {
                    "role": "user",
                    "content": f"{prompt}\n\nVoici le contenu COMPLET du document:\n\n{text[:50000]}"
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
            max_tokens=4096,
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
    print("=" * 80)
    print("RÉPONSE CLAUDE:")
    print(response_text)
    print("=" * 80)
    # Extraire le JSON
   # Extraire le JSON
    if "```json" in response_text:
        json_str = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        json_str = response_text.split("```")[1].split("```")[0].strip()
    else:
        # Cherche le premier { et le dernier }
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start != -1 and end > start:
            json_str = response_text[start:end]
        else:
            json_str = response_text.strip()

        print("JSON EXTRAIT:")
    print(json_str)
    print("=" * 80)
    
    try:
        extracted_data = json.loads(json_str)
        print("✅ JSON parsé avec succès")
        print(f"Type: {type(extracted_data)}")
        print(f"Keys: {list(extracted_data.keys())[:5]}")  # Premiers 5 keys
        return extracted_data
    except Exception as e:
        print(f"❌ ERREUR JSON PARSE: {e}")
        print(f"json_str = {json_str[:200]}")
        raise