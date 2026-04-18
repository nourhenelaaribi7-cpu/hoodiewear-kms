# generate_ocr.py
"""
Génère des images contenant du texte HoodieWear
et extrait le texte via Tesseract OCR
"""
import os
import json

IMAGES_CONTENT = [
    {
        "id":      "img_faq_livraison",
        "titre":   "FAQ Livraison HoodieWear",
        "contenu": """FAQ LIVRAISON HOODIEWEAR

Q: Quels sont vos delais de livraison ?
R: Tunisie : 3 a 5 jours ouvres. Europe : 5 a 10 jours. International : 10 a 15 jours.

Q: Comment suivre ma commande ?
R: Un email avec lien de suivi vous est envoye apres expedition. Suivez aussi dans votre espace client.

Q: Livrez-vous partout en Tunisie ?
R: Oui, dans toutes les gouvernorats via Aramex et Jumia Logistics.

Q: Que faire si ma commande n arrive pas ?
R: Apres 7 jours ouvres sans reception, contactez support@hoodiewear.com""",
        "tags":   ["livraison", "suivi", "délais", "faq"],
        "source": "ocr_faq_livraison"
    },
    {
        "id":      "img_politique_retour",
        "titre":   "Politique de Retour HoodieWear",
        "contenu": """POLITIQUE DE RETOUR ET REMBOURSEMENT

Delai de retour : 30 jours apres reception
Conditions : Article non porte, etiquettes intactes, emballage origine

PROCEDURE DE RETOUR :
1. Contactez support@hoodiewear.com avec votre numero de commande
2. Recevez votre bon de retour par email
3. Deposez le colis dans un point relais agree
4. Remboursement sous 5 a 7 jours ouvres apres reception

EXCEPTIONS :
- Articles en promotion : echange uniquement
- Articles personnalises : non retournables
- Defauts de fabrication : pris en charge par HoodieWear""",
        "tags":   ["retour", "remboursement", "politique", "échange"],
        "source": "ocr_politique_retour"
    },
    {
        "id":      "img_guide_tailles",
        "titre":   "Guide des Tailles HoodieWear",
        "contenu": """GUIDE DES TAILLES HOODIEWEAR

HOODIES ET SWEATS :
XS : Tour de poitrine 80-85 cm  Longueur 63 cm
S  : Tour de poitrine 86-91 cm  Longueur 65 cm
M  : Tour de poitrine 92-97 cm  Longueur 68 cm
L  : Tour de poitrine 98-103 cm Longueur 71 cm
XL : Tour de poitrine 104-109 cm Longueur 74 cm
XXL: Tour de poitrine 110-116 cm Longueur 77 cm

CONSEILS :
- Pour un style oversized : prenez une taille au-dessus
- Pour un style fitted : gardez votre taille habituelle
- En cas de doute : optez pour la plus grande
- Nos hoodies retrécissent légèrement au lavage (2-3%)

Contact tailles : tailles@hoodiewear.com""",
        "tags":   ["tailles", "guide", "hoodie", "mesures"],
        "source": "ocr_guide_tailles"
    },
    {
        "id":      "img_entretien",
        "titre":   "Guide Entretien HoodieWear",
        "contenu": """GUIDE D ENTRETIEN DE VOS ARTICLES HOODIEWEAR

LAVAGE :
- Temperature maximale : 30 degres
- Lavage a l envers pour preserver les couleurs
- Evitez les produits chlores
- Utilisez une lessive douce

SECHAGE :
- Sechage a l air libre recommande
- Evitez le seche-linge (risque de retrecissement)
- Ne pas essorer a haute vitesse
- Sechez a plat pour conserver la forme

REPASSAGE :
- Repassez a l envers a basse temperature (max 110 degres)
- Evitez de repasser sur les impressions
- Utilisez un linge humide entre le fer et le vetement

STOCKAGE :
- Pliez plutot que suspendrez
- Stockez dans un endroit sec et ventile""",
        "tags":   ["entretien", "lavage", "séchage", "qualité"],
        "source": "ocr_entretien"
    },
    {
        "id":      "img_paiement",
        "titre":   "Modes de Paiement HoodieWear",
        "contenu": """MODES DE PAIEMENT ACCEPTES

PAIEMENT EN LIGNE :
- Carte bancaire Visa / Mastercard (3D Secure)
- PayPal
- Virement bancaire (delai supplementaire 2-3 jours)

PAIEMENT A LA LIVRAISON :
- Disponible uniquement en Tunisie
- Especes uniquement
- Supplement de 3 DT pour ce mode de paiement

SECURITE :
- Toutes les transactions sont chiffrees SSL
- Nous ne stockons aucune donnee bancaire
- Paiement securise par notre partenaire Stripe

EN CAS DE PROBLEME :
- Double prelevement : remboursement sous 5-7 jours
- Paiement refuse : verifiez votre plafond CB
- Contact : paiement@hoodiewear.com""",
        "tags":   ["paiement", "carte", "paypal", "sécurité"],
        "source": "ocr_paiement"
    }
]


def generate_images_with_pillow():
    """Génère de vraies images PNG lisibles par Tesseract"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import textwrap

        os.makedirs("data/images", exist_ok=True)
        print("🖼️  Génération des images avec Pillow...")

        for item in IMAGES_CONTENT:
            img_path = f"data/images/{item['id']}.png"

            # Crée l'image — fond blanc, texte noir bien lisible
            width, height = 900, 1100
            img  = Image.new("RGB", (width, height), color=(255, 255, 255))
            draw = ImageDraw.Draw(img)

            # Essaie de charger une police système lisible par Tesseract
            try:
                font_title = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 22)
                font_body  = ImageFont.truetype("C:/Windows/Fonts/arial.ttf",   18)
            except Exception:
                font_title = ImageFont.load_default()
                font_body  = ImageFont.load_default()

            # Bande de titre
            draw.rectangle([0, 0, width, 55], fill=(20, 30, 80))
            draw.text((20, 14), item["titre"], fill=(255, 255, 255), font=font_title)

            # Contenu — ligne par ligne avec retour à la ligne
            y = 75
            for line in item["contenu"].split("\n"):
                wrapped = textwrap.wrap(line, width=80) if line.strip() else [""]
                for wl in wrapped:
                    draw.text((25, y), wl, fill=(20, 20, 20), font=font_body)
                    y += 24
                if not line.strip():
                    y += 6

            img.save(img_path, dpi=(300, 300))
            print(f"  ✅ {item['id']}.png créé (300 DPI)")

        return True

    except ImportError:
        print("  ❌ Pillow non disponible — pip install pillow")
        return False


def extract_text_ocr():
    """
    Extrait le texte des images via Tesseract OCR.
    Fallback automatique sur le texte source si Tesseract absent.
    """
    os.makedirs("data/raw", exist_ok=True)
    results = []

    print("\n🔍 Extraction OCR Tesseract en cours...")

    # Chemins Tesseract possibles sur Windows
    TESSERACT_PATHS = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\PC\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
    ]

    tesseract_ok = False
    for item in IMAGES_CONTENT:
        img_path       = f"data/images/{item['id']}.png"
        extracted_text = None

        if os.path.exists(img_path):
            try:
                import pytesseract
                from PIL import Image

                # Configure le chemin Tesseract
                for path in TESSERACT_PATHS:
                    if os.path.exists(path):
                        pytesseract.pytesseract.tesseract_cmd = path
                        tesseract_ok = True
                        break

                if tesseract_ok:
                    img  = Image.open(img_path)
                    text = pytesseract.image_to_string(img, lang="fra+eng")

                    if len(text.strip()) > 50:
                        extracted_text = text.strip()
                        print(f"  ✅ {item['id']} — OCR Tesseract réel ({len(extracted_text)} chars)")
                    else:
                        print(f"  ⚠️  {item['id']} — OCR trop court, texte source utilisé")

            except ImportError:
                print(f"  ⚠️  pytesseract non installé → pip install pytesseract")
            except Exception as e:
                print(f"  ⚠️  Erreur OCR {item['id']} : {e}")

        # Fallback : texte source (simulation réaliste)
        if not extracted_text:
            extracted_text = item["contenu"]
            if not tesseract_ok:
                print(f"  📝 {item['id']} — texte source (Tesseract non installé)")

        # Découpe en chunks pour le RAG
        chunks = chunk_text(extracted_text)
        for j, chunk in enumerate(chunks):
            results.append({
                "id":        f"{item['id']}_chunk_{j+1}",
                "source":    item["source"],
                "question":  f"Information extraite de : {item['titre']}",
                "reponse":   chunk,
                "tags":      item["tags"],
                "mots_cles": item["tags"],
                "type":      "ocr_extraction",
                "methode":   "tesseract-ocr" if tesseract_ok else "texte_source",
                "langue":    "fr"
            })

    # Sauvegarde JSON
    output_path = "data/raw/ocr_extractions.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    methode = "Tesseract OCR réel ✅" if tesseract_ok else "Texte source (Tesseract absent) 📝"
    print(f"\n✅ {len(results)} extractions → {output_path}")
    print(f"   Méthode utilisée : {methode}")
    return results


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> list:
    """Découpe un texte en chunks avec chevauchement"""
    chunks = []
    start  = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end].strip())
        start += chunk_size - overlap
    return [c for c in chunks if len(c) > 50]


if __name__ == "__main__":
    print("=" * 60)
    print("🖼️  Pipeline Images → OCR → JSON")
    print("=" * 60)

    generate_images_with_pillow()
    results = extract_text_ocr()

    print(f"\n🎉 Pipeline terminé ! {len(results)} chunks prêts dans data/raw/")

    # Résumé fichiers
    print("\nFichiers générés :")
    for folder in ["data/images", "data/raw"]:
        if os.path.exists(folder):
            for f in os.listdir(folder):
                size = os.path.getsize(os.path.join(folder, f))
                print(f"  📄 {folder}/{f} ({size/1024:.1f} KB)")