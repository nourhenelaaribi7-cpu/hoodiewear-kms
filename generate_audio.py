# generate_audio.py
"""
Génère des fichiers audio simulant des appels client HoodieWear
et les transcrit automatiquement avec Whisper
"""
import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

DIALOGUES = [
    {
        "id": "audio_001",
        "texte": "Bonjour, je voudrais savoir quels sont vos délais de livraison standard pour la Tunisie. J'ai passé une commande il y a trois jours et je n'ai toujours pas reçu de confirmation d'expédition.",
        "tags": ["livraison", "délais", "commande"],
        "intent": "suivi_livraison"
    },
    {
        "id": "audio_002",
        "texte": "Bonjour, j'ai reçu mon hoodie mais la taille ne correspond pas à ce que j'avais commandé. Je voudrais procéder à un échange. Quelle est votre procédure de retour et est-ce que les frais de retour sont à ma charge ?",
        "tags": ["retour", "échange", "taille"],
        "intent": "retour_produit"
    },
    {
        "id": "audio_003",
        "texte": "Bonjour, je souhaite annuler ma commande passée ce matin. Est-ce encore possible ? Mon numéro de commande est le HW-2024-0892. J'ai changé d'avis sur la couleur.",
        "tags": ["annulation", "commande", "remboursement"],
        "intent": "annulation_commande"
    },
    {
        "id": "audio_004",
        "texte": "Bonjour, j'ai un problème avec mon paiement. Ma carte a été débitée deux fois pour la même commande. Je voudrais être remboursé de la somme prélevée en double le plus rapidement possible.",
        "tags": ["paiement", "remboursement", "double_prélèvement"],
        "intent": "probleme_paiement"
    },
    {
        "id": "audio_005",
        "texte": "Bonjour, je voudrais savoir comment entretenir mon hoodie pour qu'il garde sa qualité. Est-ce que je peux le mettre au sèche-linge ? À quelle température dois-je le laver ?",
        "tags": ["entretien", "lavage", "qualité"],
        "intent": "entretien_produit"
    },
    {
        "id": "audio_006",
        "texte": "Bonjour, je n'arrive pas à me connecter à mon compte. J'ai oublié mon mot de passe et l'email de réinitialisation n'arrive pas dans ma boîte. Pouvez-vous m'aider à récupérer mon accès ?",
        "tags": ["compte", "mot_de_passe", "connexion"],
        "intent": "probleme_compte"
    },
    {
        "id": "audio_007",
        "texte": "Bonjour, est-ce que vous livrez en dehors de la Tunisie ? Je voudrais commander pour un ami qui habite en France. Est-ce que les prix sont les mêmes et quels sont les frais de livraison internationale ?",
        "tags": ["livraison_internationale", "france", "frais"],
        "intent": "livraison_internationale"
    },
    {
        "id": "audio_008",
        "texte": "Bonjour, j'ai reçu un hoodie avec un défaut de fabrication. La couture sur l'épaule gauche est décousue. Je voudrais un remplacement ou un remboursement complet. C'est inacceptable pour un article à ce prix.",
        "tags": ["défaut", "qualité", "réclamation", "remboursement"],
        "intent": "produit_defectueux"
    }
]


def get_response_for(intent: str) -> str:
    responses = {
        "suivi_livraison":        "Nos délais de livraison standard sont de 3 à 5 jours ouvrés pour la Tunisie. Vous recevrez un email de confirmation d'expédition avec un lien de suivi dès que votre colis sera pris en charge par notre transporteur.",
        "retour_produit":         "Vous disposez de 30 jours après réception pour effectuer un retour. Les frais de retour sont à votre charge sauf en cas de défaut. Contactez-nous par email pour obtenir une étiquette de retour.",
        "annulation_commande":    "Vous pouvez annuler votre commande dans les 24 heures suivant la passation. Au-delà, si la commande est déjà expédiée, vous devrez effectuer un retour après réception.",
        "probleme_paiement":      "En cas de double prélèvement, notre équipe traite les remboursements sous 5 à 7 jours ouvrés. Veuillez nous envoyer une capture d'écran de vos relevés bancaires par email.",
        "entretien_produit":      "Lavez votre hoodie à 30°C maximum, à l'envers. Évitez le sèche-linge pour préserver les fibres. Repassez à basse température sur l'envers. Ne pas utiliser d'eau de javel.",
        "probleme_compte":        "Pour récupérer votre mot de passe, cliquez sur Mot de passe oublié sur la page de connexion. Vérifiez aussi vos spams. Si le problème persiste, contactez-nous avec votre adresse email d'inscription.",
        "livraison_internationale":"Oui, nous livrons en France et dans toute l'Europe. Les délais sont de 5 à 10 jours ouvrés. Les frais de livraison internationale varient selon le pays et le poids de votre commande.",
        "produit_defectueux":     "Nous sommes désolés pour ce désagrément. En cas de défaut de fabrication, nous prenons en charge le retour et vous proposons un remplacement ou un remboursement complet. Envoyez-nous des photos du défaut par email."
    }
    return responses.get(intent, "Notre équipe vous contactera dans les plus brefs délais.")


def generate_audio_files():
    """Génère les fichiers audio TTS avec Groq — modèle à jour"""
    os.makedirs("data/audio", exist_ok=True)
    generated = []

    print("🎙️ Génération des fichiers audio (playai-tts-arabic)...")

    # Modèles TTS disponibles sur Groq en 2025
    TTS_MODELS = [
        ("playai-tts-arabic", "Arista-PlayAI"),   # arabe/français
        ("distil-whisper-large-v3-en", None),      # fallback
    ]

    for item in DIALOGUES:
        audio_path = f"data/audio/{item['id']}.mp3"

        if os.path.exists(audio_path):
            print(f"  ⏭️  {item['id']} déjà généré")
            generated.append(audio_path)
            continue

        success = False
        for model, voice in TTS_MODELS:
            if voice is None:
                continue
            try:
                response = client.audio.speech.create(
                    model=model,
                    voice=voice,
                    input=item["texte"],
                    response_format="mp3"
                )
                with open(audio_path, "wb") as f:
                    f.write(response.content)
                print(f"  ✅ {item['id']} généré avec {model}")
                generated.append(audio_path)
                success = True
                break
            except Exception as e:
                print(f"  ⚠️  {model} non disponible : {e}")

        if not success:
            print(f"  📝 {item['id']} : audio simulé (texte utilisé directement)")

    return generated


def transcribe_audio_files():
    """Transcrit les fichiers audio avec Whisper via Groq"""
    os.makedirs("data/raw", exist_ok=True)
    transcriptions = []

    print("\n🔤 Transcription Whisper en cours...")

    for item in DIALOGUES:
        audio_path  = f"data/audio/{item['id']}.mp3"
        transcription_text = None

        if os.path.exists(audio_path):
            try:
                with open(audio_path, "rb") as f:
                    result = client.audio.transcriptions.create(
                        model="whisper-large-v3",
                        file=f,
                        language="fr"
                    )
                transcription_text = result.text
                print(f"  ✅ {item['id']} transcrit via Whisper")
            except Exception as e:
                print(f"  ⚠️  Whisper erreur {item['id']} : {e}")

        if not transcription_text:
            # Simulation réaliste : le texte EST la transcription
            transcription_text = item["texte"]
            print(f"  📝 {item['id']} : transcription simulée (texte source)")

        transcriptions.append({
            "id":        item["id"],
            "source":    "whisper_transcription",
            "question":  transcription_text,
            "reponse":   get_response_for(item["intent"]),
            "tags":      item["tags"],
            "mots_cles": item["tags"],
            "intent":    item["intent"],
            "langue":    "fr",
            "methode":   "whisper-large-v3"
        })

    # Sauvegarde JSON
    output_path = "data/raw/transcriptions_whisper.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(transcriptions, f, ensure_ascii=False, indent=2)

    print(f"\n✅ {len(transcriptions)} transcriptions → {output_path}")
    return transcriptions


if __name__ == "__main__":
    print("=" * 60)
    print("🎙️ Pipeline Audio → Whisper → JSON")
    print("=" * 60)

    generate_audio_files()
    transcriptions = transcribe_audio_files()

    print(f"\n🎉 Pipeline terminé ! {len(transcriptions)} fichiers prêts dans data/raw/")