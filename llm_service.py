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
    Extrait les données financières d'un document bancaire UEMOA.
    
    Supporte:
    - PDFs avec texte extractible (lecture directe)
    - PDFs scannés (OCR sur TOUTES les pages, puis texte à Claude)
    - Images directes (JPG, PNG)
    
    Returns:
        dict: Données financières au format JSON
    """
    
    # ========================================
    # PROMPT CLAUDE (identique pour tous)
    # ========================================
    
    prompt = """
Tu es un expert financier bancaire spécialisé dans la zone UEMOA (Union Économique et Monétaire Ouest-Africaine).

Ta mission: Extraire TOUTES les données du bilan et du compte de résultat.

INSTRUCTIONS CRITIQUES:
- Le document peut contenir 30+ pages, mais seules 3-5 pages sont importantes
- Concentre-toi sur les sections: "BILAN", "BALANCE SHEET", "COMPTE DE RÉSULTAT", "INCOME STATEMENT"
- Ignore les notes annexes détaillées
- Les montants sont en milliers (KCFA ou MXOF)

═══════════════════════════════════════════════════════════════════════════════
BILAN - ACTIFS (cherche ces intitulés exacts ou similaires):
═══════════════════════════════════════════════════════════════════════════════

- cash_reserves_requirements → "Caisse et Banque Centrale" / "Caisse" / "Cash & Central Bank"
- due_from_banks → "Correspondants bancaires" / "Banques et établissements financiers" / "Due from Banks"
- investment_securities → "Titres de placement" / "Portefeuille-titres" / "Investment Securities"
- gross_loans → "Crédits à la clientèle" (BRUT, avant provisions) / "Loans to Customers" / "Gross Loans"
- loan_loss_provisions → "Provisions pour créances douteuses" / "Loan Loss Provisions" (valeur NÉGATIVE si provision)
- foreclosed_assets → "Actifs saisis" / "Foreclosed Assets"
- fixed_assets → "Immobilisations" / "Fixed Assets" / "Property & Equipment"
- other_assets → "Autres actifs"
- total_assets → "TOTAL ACTIF" / "TOTAL ASSETS" (⚠️ OBLIGATOIRE)

IMPORTANT POUR LES NPL:
- npls_mn → Cherche "Créances en souffrance" / "NPL" / "Non-performing loans" - SI ABSENT, utilise la valeur absolue de loan_loss_provisions
- llr_mn → Cherche "Provisions sur créances" / "LLR" / "Loan Loss Reserves" - SI ABSENT, utilise la valeur absolue de loan_loss_provisions

═══════════════════════════════════════════════════════════════════════════════
BILAN - PASSIFS:
═══════════════════════════════════════════════════════════════════════════════

- deposits → "Dépôts de la clientèle" / "Customer Deposits" / "Dépôts à vue + à terme"
- interbank_liabilities → "Dettes envers les établissements de crédit"
- other_liabilities → "Autres passifs"
- total_liabilities → "TOTAL PASSIF" / "Total Liabilities"

═══════════════════════════════════════════════════════════════════════════════
BILAN - CAPITAUX PROPRES (EQUITY):
═══════════════════════════════════════════════════════════════════════════════

- paid_in_capital → "Capital social" / "Share Capital"
- reserves → "Réserves" / "Reserves"
- retained_earnings → "Report à nouveau" / "Retained Earnings"
- net_profit → "Résultat de l'exercice" / "Net Profit"
- total_equity → "CAPITAUX PROPRES" / "Total Equity" / "Fonds propres" (⚠️ OBLIGATOIRE)

═══════════════════════════════════════════════════════════════════════════════
COMPTE DE RÉSULTAT (INCOME STATEMENT):
═══════════════════════════════════════════════════════════════════════════════

- interest_income → "Produits d'intérêts" / "Interest Income"
- interest_expenses → "Charges d'intérêts" / "Interest Expenses"
- net_interest_income → "Produit net bancaire" / "Marge nette d'intérêt" / "Net Interest Income"
- non_interest_income_commissions → "Commissions" / "Fee Income" / "Commissions reçues"
- net_income_investment → "Produits des investissements"
- other_net_income → "Autres produits nets"
- operating_expenses → "Frais généraux" / "Operating Expenses" / "Charges de personnel + autres charges"
- operating_profit → "Résultat d'exploitation"
- provision_expenses → "Dotations aux provisions" / "Provision Expenses"
- non_operating_profit_loss → "Résultat hors exploitation"
- income_tax → "Impôts" / "Income Tax"
- net_income → "RÉSULTAT NET" / "NET INCOME" / "Bénéfice net" (⚠️ OBLIGATOIRE)

═══════════════════════════════════════════════════════════════════════════════
RATIOS PRUDENTIELS:
═══════════════════════════════════════════════════════════════════════════════

- car_regulatory → "Ratio de solvabilité" / "CAR" / "Capital Adequacy Ratio" (format: 13.42 pour 13.42%)
- car_bank_reported → "CAR déclaré par la banque"
CHERCHE CES RATIOS DÉJÀ CALCULÉS DANS LE DOCUMENT (section "Ratios", "Indicateurs", "Principaux ratios de gestion"):

**SOLVABILITÉ:**
- car_regulatory → "Ratio de solvabilité" / "CAR" / "Capital Adequacy Ratio" (format: 13.42 pour 13.42%)
- car_bank_reported → "CAR déclaré par la banque"

**QUALITÉ DES ACTIFS:**
- npl_ratio_reported → "Taux de créances en souffrance" / "NPL Ratio" / "Créances douteuses / Crédits bruts" (format: 5.2 pour 5.2%)
- coverage_ratio_reported → "Taux de couverture" / "Coverage Ratio" / "Couverture des créances douteuses" (format: 95.5 pour 95.5%)

**RENTABILITÉ:**
- roe_reported → "ROE" / "Rentabilité économique" / "Return on Equity" (format: 28.51 pour 28.51%)
- roa_reported → "ROA" / "Rentabilité des actifs" / "Return on Assets" (format: 2.59 pour 2.59%)
- cost_income_reported → "Coefficient d'exploitation" / "Cost to Income" / "Ratio d'efficience" (format: 45.09 pour 45.09%)
═══════════════════════════════════════════════════════════════════════════════
FORMAT DE SORTIE (JSON UNIQUEMENT):
═══════════════════════════════════════════════════════════════════════════════

⚠️ NE RETOURNE QUE LE JSON - PAS DE TEXTE AVANT OU APRÈS
⚠️ Utilise null pour les valeurs manquantes (pas de 0 ou de valeurs inventées)
⚠️ TOUS les montants en VALEUR ABSOLUE sauf loan_loss_provisions (négatif)

{
    "name": "Nom de la banque",
    "country": "Sénégal",
    "fiscal_year": "2023" ou "2022-2023",
    "currency": "XOF",
    "total_assets": 700000,
    "cash_reserves_requirements": 50000,
    "due_from_banks": 20000,
    "investment_securities": 100000,
    "gross_loans": 500000,
    "loan_loss_provisions": -25000,
    "foreclosed_assets": null,
    "fixed_assets": 30000,
    "other_assets": 25000,
    "deposits": 550000,
    "interbank_liabilities": null,
    "other_liabilities": 50000,
    "total_liabilities": 600000,
    "paid_in_capital": 60000,
    "reserves": 30000,
    "retained_earnings": 5000,
    "net_profit": 5000,
    "total_equity": 100000,
    "interest_income": 60000,
    "interest_expenses": 20000,
    "net_interest_income": 40000,
    "non_interest_income_commissions": 10000,
    "net_income_investment": null,
    "other_net_income": null,
    "operating_expenses": 30000,
    "operating_profit": null,
    "provision_expenses": 10000,
    "non_operating_profit_loss": null,
    "income_tax": 5000,
    "net_income": 5000,
    "car_regulatory": 14.3,
    "car_bank_reported": null,
    "npls_mn": 25000,
    "llr_mn": 25000
    "npl_ratio_reported": 4.55,
    "coverage_ratio_reported": 95.5,
    "roe_reported": 28.51,
    "roa_reported": 2.59,
    "cost_income_reported": 45.09
}
"""
    
    # ========================================
    # SECTION 1: ENVOI À CLAUDE
    # (différent selon le type de fichier)
    # ========================================
    
    if file_path.lower().endswith('.pdf'):
        print("📄 Traitement d'un fichier PDF...")
        
        # Tenter l'extraction de texte
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        
        # Vérifier si le PDF est scanné (texte vide/très court)
        if len(text.strip()) < 100:
            # ═══════════════════════════════════════════════════════════
            # PDF SCANNÉ → OCR sur TOUTES les pages
            # ═══════════════════════════════════════════════════════════
            
            print("⚠️  PDF SCANNÉ détecté - Extraction OCR sur TOUTES les pages...")
            from pdf2image import convert_from_path
            import pytesseract
            
            # Convertir TOUTES les pages en images (pas de limite)
            print("🔄 Conversion du PDF en images (peut prendre 30s-2min pour gros fichiers)...")
            images = convert_from_path(
                file_path,
                dpi=150  # DPI réduit pour vitesse (suffisant pour OCR)
            )
            
            if not images:
                raise Exception("❌ Échec de la conversion PDF → Images")
            
            print(f"✅ {len(images)} page(s) convertie(s) en images")
            
            # OCR sur TOUTES les pages
            print("🔍 Extraction du texte via OCR (Tesseract)...")
            full_text = ""
            
            for i, img in enumerate(images):
                print(f"   📄 Page {i+1}/{len(images)}...", end=" ")
                
                # OCR avec Tesseract (français + anglais)
                try:
                    page_text = pytesseract.image_to_string(
                        img, 
                        lang='fra+eng',  # Français + Anglais
                        config='--psm 6'  # Assume uniform block of text
                    )
                    full_text += f"\n\n{'='*80}\nPAGE {i+1}\n{'='*80}\n\n{page_text}"
                    print(f"✅ ({len(page_text)} chars)")
                except Exception as e:
                    print(f"⚠️  Erreur OCR: {e}")
            
            print(f"\n✅ Extraction OCR terminée: {len(full_text)} caractères au total")
            
            # Envoyer le TEXTE à Claude (pas les images)
            print("🚀 Envoi du texte OCR à Claude...")
            message = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": f"{prompt}\n\n{'='*80}\nDOCUMENT EXTRAIT PAR OCR:\n{'='*80}\n\n{full_text[:100000]}"
                    # ↑ Limite à 100k chars pour éviter dépassement tokens
                }]
            )
        
        else:
            # ═══════════════════════════════════════════════════════════
            # PDF avec texte extractible → Envoi direct du texte
            # ═══════════════════════════════════════════════════════════
            
            print(f"✅ PDF avec texte extractible ({len(text)} caractères)")
            print("🚀 Envoi à Claude (mode texte)...")
            
            message = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": f"{prompt}\n\n{'='*80}\nDOCUMENT À ANALYSER:\n{'='*80}\n\n{text[:100000]}"
                }]
            )
    
    else:
        # ═══════════════════════════════════════════════════════════
        # IMAGE DIRECTE (JPG/PNG) → OCR puis texte
        # ═══════════════════════════════════════════════════════════
        
        print(f"🖼️  Image directe détectée: {file_path}")
        
        from PIL import Image
        import pytesseract
        
        img = Image.open(file_path)
        print("🔍 Extraction du texte via OCR...")
        
        image_text = pytesseract.image_to_string(
            img,
            lang='fra+eng',
            config='--psm 6'
        )
        
        print(f"✅ Texte extrait: {len(image_text)} caractères")
        print("🚀 Envoi à Claude...")
        
        message = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": f"{prompt}\n\n{'='*80}\nDOCUMENT EXTRAIT PAR OCR:\n{'='*80}\n\n{image_text}"
            }]
        )
    
    # ========================================
    # SECTION 2: PARSING DE LA RÉPONSE
    # (identique pour TOUS les types)
    # ========================================
    
    response_text = message.content[0].text
    
    print("\n" + "="*80)
    print("📥 RÉPONSE BRUTE DE CLAUDE:")
    print("="*80)
    preview = response_text[:500] + "..." if len(response_text) > 500 else response_text
    print(preview)
    print("="*80 + "\n")
    
    # ───────────────────────────────────────────────────────────────
    # Extraction du JSON
    # ───────────────────────────────────────────────────────────────
    
    json_str = response_text.strip()
    
    if "```json" in response_text:
        json_str = response_text.split("```json")[1].split("```")[0].strip()
        print("✅ JSON extrait depuis bloc markdown (```json)")
    elif "```" in response_text:
        json_str = response_text.split("```")[1].split("```")[0].strip()
        print("✅ JSON extrait depuis bloc markdown (```)")
    else:
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start != -1 and end > start:
            json_str = response_text[start:end]
            print("✅ JSON extrait par recherche de { }")
    
    print("\n" + "="*80)
    print("📋 JSON EXTRAIT:")
    print("="*80)
    preview_json = json_str[:300] + "..." if len(json_str) > 300 else json_str
    print(preview_json)
    print("="*80 + "\n")
    
    # ───────────────────────────────────────────────────────────────
    # Parsing JSON
    # ───────────────────────────────────────────────────────────────
    
    try:
        extracted_data = json.loads(json_str)
        
        print("✅ JSON parsé avec succès!")
        print(f"   - Banque: {extracted_data.get('name', 'N/A')}")
        print(f"   - Année: {extracted_data.get('fiscal_year', 'N/A')}")
        print(f"   - Total Assets: {extracted_data.get('total_assets', 'N/A')}")
        print(f"   - Total Equity: {extracted_data.get('total_equity', 'N/A')}")
        print(f"   - Net Income: {extracted_data.get('net_income', 'N/A')}")
        
        print("\n" + "=" * 80)
        print("📋 JSON COMPLET:")
        print("=" * 80)
        print(json.dumps(extracted_data, indent=2))
        print("=" * 80 + "\n")
        
        return extracted_data
        
    except json.JSONDecodeError as e:
        print(f"❌ ERREUR DE PARSING JSON!")
        print(f"   Message: {str(e)}")
        print(f"   Position: ligne {e.lineno}, colonne {e.colno}")
        print("\n" + "="*80)
        print("📄 CONTENU QUI A ÉCHOUÉ:")
        print("="*80)
        print(json_str[:200])
        print("="*80 + "\n")
        raise Exception(f"JSON invalide retourné par Claude: {str(e)}")