# generate_data.py
"""
Génère les fichiers JSON et CSV structurés
avec tags et mots-clés pour le RAG HoodieWear
"""
import os
import json
import csv

# ── FAQ structurée JSON ────────────────────────────────────────────────────────
FAQ_DATA = [
    {
        "id": "faq_001",
        "question": "Quels sont vos délais de livraison ?",
        "reponse": "Nos délais de livraison sont de 3 à 5 jours ouvrés pour la Tunisie, 5 à 10 jours pour l'Europe, et 10 à 15 jours pour le reste du monde.",
        "tags": ["livraison", "délais", "expédition"],
        "mots_cles": ["livraison", "délai", "jours", "expédition", "réception"],
        "intent": "info_livraison",
        "categorie": "livraison"
    },
    {
        "id": "faq_002",
        "question": "Comment retourner un article ?",
        "reponse": "Pour retourner un article, envoyez un email à support@hoodiewear.com avec votre numéro de commande. Vous avez 30 jours après réception pour effectuer un retour. Les articles doivent être non portés avec étiquettes intactes.",
        "tags": ["retour", "remboursement", "échange"],
        "mots_cles": ["retour", "renvoi", "remboursement", "échange", "retourner"],
        "intent": "retour_article",
        "categorie": "retour"
    },
    {
        "id": "faq_003",
        "question": "Comment suivre ma commande ?",
        "reponse": "Après expédition, vous recevez un email avec un numéro de suivi. Vous pouvez suivre votre colis sur notre site dans la rubrique 'Mon compte > Mes commandes' ou directement sur le site de notre transporteur.",
        "tags": ["suivi", "commande", "tracking", "colis"],
        "mots_cles": ["suivi", "tracking", "commande", "colis", "livraison", "où"],
        "intent": "suivi_commande",
        "categorie": "commande"
    },
    {
        "id": "faq_004",
        "question": "Quelles tailles sont disponibles ?",
        "reponse": "Nous proposons les tailles XS, S, M, L, XL et XXL. Consultez notre guide des tailles pour choisir la bonne. Pour un style oversized, prenez une taille au-dessus de votre taille habituelle.",
        "tags": ["tailles", "guide", "mesures", "XS", "XXL"],
        "mots_cles": ["taille", "tailles", "XS", "S", "M", "L", "XL", "XXL", "mesures", "guide"],
        "intent": "info_tailles",
        "categorie": "produit"
    },
    {
        "id": "faq_005",
        "question": "Comment récupérer mon mot de passe ?",
        "reponse": "Cliquez sur 'Mot de passe oublié' sur la page de connexion, entrez votre email d'inscription, et vous recevrez un lien de réinitialisation valable 24 heures. Vérifiez vos spams si vous ne le recevez pas.",
        "tags": ["compte", "mot_de_passe", "connexion", "réinitialisation"],
        "mots_cles": ["mot de passe", "oublié", "connexion", "compte", "email", "réinitialisation"],
        "intent": "recuperation_mdp",
        "categorie": "compte"
    },
    {
        "id": "faq_006",
        "question": "Quels sont les modes de paiement acceptés ?",
        "reponse": "Nous acceptons les cartes bancaires Visa et Mastercard, PayPal, et le virement bancaire. En Tunisie, le paiement à la livraison en espèces est disponible avec un supplément de 3 DT.",
        "tags": ["paiement", "carte", "paypal", "livraison"],
        "mots_cles": ["paiement", "carte", "visa", "mastercard", "paypal", "virement", "espèces"],
        "intent": "info_paiement",
        "categorie": "paiement"
    },
    {
        "id": "faq_007",
        "question": "Livrez-vous à l'international ?",
        "reponse": "Oui, nous livrons dans toute l'Europe, en Afrique du Nord et dans certains pays du Moyen-Orient. Les délais varient de 5 à 15 jours selon la destination. Les frais de port international sont calculés à la commande.",
        "tags": ["international", "livraison", "europe", "afrique"],
        "mots_cles": ["international", "europe", "france", "algérie", "maroc", "livraison", "étranger"],
        "intent": "livraison_internationale",
        "categorie": "livraison"
    },
    {
        "id": "faq_008",
        "question": "Puis-je annuler ma commande ?",
        "reponse": "Vous pouvez annuler votre commande gratuitement dans les 24 heures suivant la passation en nous contactant par email. Au-delà, si la commande est expédiée, vous devrez attendre la réception et effectuer un retour.",
        "tags": ["annulation", "commande", "remboursement"],
        "mots_cles": ["annuler", "annulation", "commande", "24h", "modifier"],
        "intent": "annulation_commande",
        "categorie": "commande"
    },
    {
        "id": "faq_009",
        "question": "Comment laver mon hoodie HoodieWear ?",
        "reponse": "Lavez votre hoodie à 30°C maximum, à l'envers, avec une lessive douce. Évitez le sèche-linge et l'eau de javel. Séchez à l'air libre et repassez à basse température à l'envers pour préserver les couleurs et les impressions.",
        "tags": ["entretien", "lavage", "hoodie", "qualité"],
        "mots_cles": ["laver", "lavage", "hoodie", "entretien", "température", "sèche-linge"],
        "intent": "entretien_produit",
        "categorie": "produit"
    },
    {
        "id": "faq_010",
        "question": "Mon article est défectueux, que faire ?",
        "reponse": "En cas de défaut de fabrication, contactez-nous immédiatement avec des photos du défaut. Nous prenons en charge le retour et vous proposons un remplacement ou un remboursement complet selon votre préférence.",
        "tags": ["défaut", "qualité", "réclamation", "remboursement"],
        "mots_cles": ["défectueux", "défaut", "qualité", "cassé", "abîmé", "couture", "problème"],
        "intent": "produit_defectueux",
        "categorie": "qualite"
    },
    {
        "id": "faq_011",
        "question": "Avez-vous une boutique physique ?",
        "reponse": "HoodieWear est une boutique 100% en ligne. Vous pouvez commander directement sur notre site hoodiewear.com. Nous n'avons pas de boutique physique mais nous participons à des pop-up stores régulièrement annoncés sur nos réseaux sociaux.",
        "tags": ["boutique", "magasin", "en_ligne", "physique"],
        "mots_cles": ["boutique", "magasin", "physique", "adresse", "visiter", "pop-up"],
        "intent": "info_boutique",
        "categorie": "general"
    },
    {
        "id": "faq_012",
        "question": "Comment contacter le service client ?",
        "reponse": "Vous pouvez contacter notre service client par email à support@hoodiewear.com (réponse sous 24h), par chat en direct sur notre site (lun-ven 9h-18h), ou via nos réseaux sociaux Instagram et Facebook.",
        "tags": ["contact", "service_client", "email", "chat"],
        "mots_cles": ["contact", "contacter", "email", "téléphone", "service client", "aide", "support"],
        "intent": "contact_service",
        "categorie": "general"
    }
]

# ── Données CSV : historique commandes simulé ──────────────────────────────────
COMMANDES_CSV = [
    ["id_commande", "statut", "delai_jours", "mode_paiement", "probleme", "resolution"],
    ["HW-2024-0001", "livré", "4", "carte", "aucun", ""],
    ["HW-2024-0002", "livré", "3", "paypal", "taille incorrecte", "échange effectué"],
    ["HW-2024-0003", "en_transit", "2", "carte", "aucun", ""],
    ["HW-2024-0004", "livré", "6", "livraison", "retard", "bon de réduction offert"],
    ["HW-2024-0005", "annulé", "0", "paypal", "annulation client", "remboursement effectué"],
    ["HW-2024-0006", "livré", "5", "virement", "défaut couture", "remplacement envoyé"],
    ["HW-2024-0007", "livré", "4", "carte", "aucun", ""],
    ["HW-2024-0008", "en_transit", "3", "carte", "aucun", ""],
    ["HW-2024-0009", "livré", "7", "livraison", "colis endommagé", "remboursement partiel"],
    ["HW-2024-0010", "livré", "3", "paypal", "aucun", ""],
]


def generate_faq_json():
    """Génère le fichier FAQ JSON structuré"""
    os.makedirs("data/raw", exist_ok=True)
    output_path = "data/raw/faq_hoodiewear.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(FAQ_DATA, f, ensure_ascii=False, indent=2)

    print(f"✅ FAQ JSON générée : {len(FAQ_DATA)} entrées → {output_path}")
    return FAQ_DATA


def generate_commandes_csv():
    """Génère le fichier CSV des commandes"""
    os.makedirs("data/raw", exist_ok=True)
    output_path = "data/raw/commandes_historique.csv"

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in COMMANDES_CSV:
            writer.writerow(row)

    print(f"✅ CSV commandes généré : {len(COMMANDES_CSV)-1} lignes → {output_path}")


def generate_procedures_json():
    """Génère un JSON de procédures internes"""
    procedures = [
        {
            "id":        "proc_001",
            "titre":     "Procédure retour standard",
            "question":  "Quelle est la procédure de retour chez HoodieWear ?",
            "reponse":   "Étape 1 : Client contacte support@hoodiewear.com avec numéro commande. Étape 2 : Agent vérifie éligibilité (30 jours, article non porté). Étape 3 : Envoi étiquette retour. Étape 4 : Réception article. Étape 5 : Remboursement sous 5-7 jours.",
            "tags":      ["retour", "procédure", "remboursement"],
            "mots_cles": ["retour", "procédure", "étapes", "remboursement"],
            "type":      "procedure_interne"
        },
        {
            "id":        "proc_002",
            "titre":     "Gestion produit défectueux",
            "question":  "Comment gérer une réclamation pour produit défectueux ?",
            "reponse":   "Étape 1 : Client envoie photos du défaut par email. Étape 2 : Agent valide le défaut de fabrication. Étape 3 : Proposition remplacement ou remboursement. Étape 4 : Envoi étiquette retour gratuite. Étape 5 : Expédition remplacement ou remboursement sous 48h.",
            "tags":      ["défaut", "réclamation", "procédure", "qualité"],
            "mots_cles": ["défaut", "défectueux", "procédure", "réclamation"],
            "type":      "procedure_interne"
        },
        {
            "id":        "proc_003",
            "titre":     "Procédure double prélèvement",
            "question":  "Que faire en cas de double prélèvement bancaire ?",
            "reponse":   "Étape 1 : Client envoie capture d'écran relevé bancaire. Étape 2 : Vérification dans le système de paiement Stripe. Étape 3 : Confirmation du double prélèvement. Étape 4 : Remboursement initié sous 24h. Étape 5 : Remboursement effectif sous 5-7 jours ouvrés selon la banque.",
            "tags":      ["paiement", "double_prélèvement", "remboursement"],
            "mots_cles": ["double", "prélèvement", "remboursement", "paiement"],
            "type":      "procedure_interne"
        }
    ]

    output_path = "data/raw/procedures_internes.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(procedures, f, ensure_ascii=False, indent=2)

    print(f"✅ Procédures JSON générées : {len(procedures)} entrées → {output_path}")
    return procedures


if __name__ == "__main__":
    print("=" * 60)
    print("📊 Génération données structurées HoodieWear")
    print("=" * 60)

    generate_faq_json()
    generate_commandes_csv()
    generate_procedures_json()

    print(f"\n🎉 Toutes les données générées dans data/raw/")
    print("\nFichiers créés :")
    for f in os.listdir("data/raw"):
        size = os.path.getsize(f"data/raw/{f}")
        print(f"  📄 {f} ({size/1024:.1f} KB)")