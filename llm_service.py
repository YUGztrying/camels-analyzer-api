# llm_service.py
import anthropic
import os
from dotenv import load_dotenv
import base64
import json
from PyPDF2 import PdfReader

# Charger les variables d'environnement
load_dotenv()

# Initialiser le client Anthropic
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def extract_bank_data_from_file(file_path: str) -> dict:
    """
    Extrait les données bancaires d'un fichier (PDF ou image).
    """
    
    # Prompt pour Claude
    prompt = """
    Analyse ce document financier et extrais les informations suivantes :
    - Nom de la banque
    - Pays
    - Total des actifs (en chiffres, sans devise ni symbole)
    
    Réponds UNIQUEMENT en JSON avec ce format exact :
    {
        "name": "Nom de la banque",
        "country": "Pays",
        "total_assets": 1234567890
    }
    
    Si tu ne trouves pas une information, mets null.
    Ne mets AUCUN texte avant ou après le JSON.
    """
    
    # Si c'est un PDF, extraire le texte
    if file_path.lower().endswith('.pdf'):
        # Lire le PDF
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        
        # Envoyer le texte à Claude
        message = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": f"{prompt}\n\nVoici le contenu du document :\n\n{text[:10000]}"
                }
            ]
        )
    
    # Si c'est une image
    else:
        with open(file_path, "rb") as f:
            file_data = base64.standard_b64encode(f.read()).decode("utf-8")
        
        # Déterminer le type de média
        if file_path.lower().endswith('.png'):
            media_type = "image/png"
        elif file_path.lower().endswith('.gif'):
            media_type = "image/gif"
        elif file_path.lower().endswith('.webp'):
            media_type = "image/webp"
        else:
            media_type = "image/jpeg"
        
        # Envoyer l'image à Claude
        message = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=1024,
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
    
    # Extraire le JSON de la réponse
    if "```json" in response_text:
        json_str = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        json_str = response_text.split("```")[1].split("```")[0].strip()
    else:
        json_str = response_text.strip()
    
    # Parser le JSON
    extracted_data = json.loads(json_str)
    
    return extracted_data