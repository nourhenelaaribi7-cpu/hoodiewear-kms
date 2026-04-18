# src/sentiment.py

# ── Dictionnaires de mots-clés ─────────────────────────────────────────────────
SENTIMENT_WORDS = {
    "frustré": [
        # Français
        "problème", "urgent", "déçu", "nul", "honte", "jamais reçu",
        "remboursement", "scandale", "arnaque", "inacceptable", "inadmissible",
        "horrible", "catastrophe", "bug", "erreur", "impossible", "bloqué",
        "en attente depuis", "toujours pas", "aucune réponse", "pas reçu",
        "commande perdue", "retard", "annuler", "réclamation", "plainte",
        # Anglais
        "problem", "issue", "terrible", "awful", "worst", "ridiculous",
        "unacceptable", "refund", "broken", "never received", "lost",
        # Arabe
        "مشكلة", "فضيحة", "مقبولش", "محتاج", "ضروري", "ما وصلش"
    ],
    "satisfait": [
        # Français
        "merci", "super", "parfait", "excellent", "bravo", "génial",
        "top", "nickel", "impeccable", "très bien", "satisfait", "content",
        "rapide", "livré rapidement", "qualité", "recommend", "j'adore",
        # Anglais
        "thank", "great", "awesome", "perfect", "amazing", "love",
        "fantastic", "wonderful", "excellent",
        # Arabe
        "شكرا", "ممتاز", "رائع", "مبروك", "جيد", "سريع"
    ],
    "urgent": [
        # Français
        "urgent", "rapidement", "immédiatement", "dès que possible",
        "asap", "vite", "aujourd'hui", "maintenant", "pressé",
        # Anglais
        "urgent", "asap", "immediately", "right now", "quickly",
        # Arabe
        "عاجل", "سريعا", "الآن", "فورا"
    ],
    "confus": [
        # Français
        "je comprends pas", "pas clair", "confused", "comment ça marche",
        "je sais pas", "expliquer", "c'est quoi", "perdu", "aide",
        # Anglais
        "confused", "don't understand", "how does", "what is", "explain",
        # Arabe
        "مفهمتش", "كيفاش", "ما عرفتش", "وضح"
    ]
}

TONE_INSTRUCTIONS = {
    "frustré": """⚠️ IMPORTANT : Le client semble frustré ou mécontent.
- Commence par t'excuser sincèrement
- Montre de l'empathie immédiatement  
- Propose une solution concrète et rapide
- Termine en rassurant le client
- Exemple de début : "Je suis vraiment désolé pour ce désagrément..." """,

    "satisfait": """😊 Le client est satisfait ou positif.
- Sois chaleureux et enthousiaste
- Remercie-le pour sa confiance
- Réponds de manière positive et énergique
- Exemple de début : "Merci pour votre message ! Je suis ravi de..." """,

    "urgent": """🚨 IMPORTANT : Le client a un besoin urgent.
- Réponds de manière directe et rapide
- Va droit au but, sans introduction longue
- Propose une solution immédiate
- Si besoin, propose de le rediriger vers un agent humain
- Exemple de début : "Je traite votre demande en priorité..." """,

    "confus": """🤔 Le client semble perdu ou confus.
- Explique de manière simple et claire
- Utilise des étapes numérotées si possible
- Évite le jargon technique
- Propose de l'aide supplémentaire à la fin
- Exemple de début : "Pas de souci, je vais vous expliquer étape par étape..." """,

    "neutre": """😐 Ton neutre et professionnel.
- Sois clair, concis et bienveillant
- Réponds directement à la question"""
}

SENTIMENT_EMOJIS = {
    "frustré":  "😤",
    "satisfait": "😊",
    "urgent":   "🚨",
    "confus":   "🤔",
    "neutre":   "😐"
}

SENTIMENT_COLORS = {
    "frustré":  "#ff4444",
    "satisfait": "#00cc44",
    "urgent":   "#ff8800",
    "confus":   "#8844ff",
    "neutre":   "#888888"
}

SENTIMENT_LABELS = {
    "frustré":  "Client frustré",
    "satisfait": "Client satisfait",
    "urgent":   "Demande urgente",
    "confus":   "Client confus",
    "neutre":   "Ton neutre"
}


def analyze_sentiment(text: str) -> dict:
    """
    Analyse le sentiment du texte et retourne un dictionnaire complet.
    
    Returns:
        dict avec keys: sentiment, emoji, color, label, tone_instruction, scores
    """
    text_lower = text.lower()
    
    # Calcule un score pour chaque sentiment
    scores = {}
    for sentiment, keywords in SENTIMENT_WORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        scores[sentiment] = score
    
    # Priorité : urgent > frustré > confus > satisfait > neutre
    priority = ["urgent", "frustré", "confus", "satisfait"]
    
    detected = "neutre"
    for sentiment in priority:
        if scores.get(sentiment, 0) > 0:
            detected = sentiment
            break
    
    return {
        "sentiment":         detected,
        "emoji":             SENTIMENT_EMOJIS[detected],
        "color":             SENTIMENT_COLORS[detected],
        "label":             SENTIMENT_LABELS[detected],
        "tone_instruction":  TONE_INSTRUCTIONS[detected],
        "scores":            scores
    }


def get_escalation_needed(sentiment: str, score: int) -> bool:
    """Détermine si une escalade vers un agent humain est nécessaire"""
    return sentiment == "frustré" and score >= 2