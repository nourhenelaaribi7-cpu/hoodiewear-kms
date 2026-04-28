"""
src/knowledge_synthesizer.py
=============================
Synthèse multi-documents — HoodieWear KMS v3.0
Adapté depuis Portalyze FivePAgent.py

Au lieu d'analyser 5 forces de Porter, ce module :
  - Fusionne plusieurs chunks ChromaDB en une réponse cohérente
  - Détecte et résout les contradictions entre sources
  - Génère un résumé structuré orienté service client

Usage :
    from src.knowledge_synthesizer import synthesize_answer
    answer = synthesize_answer(question, docs, lang)
"""

import os
import re
import json
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL_SYNTH = "llama-3.3-70b-versatile"

# ── Templates de synthèse par topic (adapté depuis PORTER_FORCE_TEMPLATES) ────
SYNTHESIS_TEMPLATES = {
    "livraison": """
Tu es l'assistant service client de HoodieWear.

CONTEXTE (plusieurs sources) :
{context}

QUESTION : {question}

Synthétise les informations sur la livraison en :
1. Donnant les délais EXACTS selon la destination
2. Mentionnant les frais si disponibles
3. Expliquant le suivi de colis
4. Restant en {lang}

Format : réponse directe max 3 phrases, sans introduction.""",

    "retour": """
Tu es l'assistant service client de HoodieWear.

CONTEXTE (plusieurs sources) :
{context}

QUESTION : {question}

Synthétise les informations sur les retours en :
1. Donnant la procédure exacte (étapes)
2. Mentionnant les délais de remboursement
3. Précisant les conditions (état article, délai)
4. Restant en {lang}

Format : réponse directe max 4 phrases.""",

    "paiement": """
Tu es l'assistant service client de HoodieWear.

CONTEXTE (plusieurs sources) :
{context}

QUESTION : {question}

Synthétise les informations sur le paiement en :
1. Listant les modes acceptés
2. Précisant les frais supplémentaires si pertinent
3. Assurant le client sur la sécurité
4. Restant en {lang}

Format : réponse directe max 3 phrases.""",

    "default": """
Tu es l'assistant service client de HoodieWear, boutique streetwear tunisienne.

CONTEXTE (plusieurs sources) :
{context}

QUESTION : {question}

Réponds de manière claire et directe en utilisant UNIQUEMENT les informations du contexte.
Si une information est absente, redirige vers support@hoodiewear.com.
Langue de réponse : {lang}
Maximum 3 phrases."""
}

TOPIC_MAP = {
    "livraison":  ["livraison", "délai", "expédition", "colis", "delivery", "shipping", "شحن"],
    "retour":     ["retour", "rembours", "échange", "return", "refund", "إرجاع"],
    "paiement":   ["paiement", "carte", "paypal", "payment", "دفع"],
    "taille":     ["taille", "size", "xl", "xxl", "mesure", "مقاس"],
    "commande":   ["commande", "annuler", "order", "cancel", "طلب"],
    "entretien":  ["laver", "lavage", "wash", "care", "غسيل"],
}

LANG_LABELS = {
    "french":  "français",
    "english": "English",
    "arabic":  "العربية",
}


def _detect_topic(question: str) -> str:
    q = question.lower()
    for topic, keywords in TOPIC_MAP.items():
        if any(kw in q for kw in keywords):
            return topic
    return "default"


def _format_multi_context(docs: list) -> str:
    """
    Formate plusieurs documents en un contexte structuré pour le LLM.
    Adapté depuis Portalyze FivePAgent.load_rags()
    """
    if not docs:
        return "Aucun document disponible."

    parts = []
    for i, doc in enumerate(docs[:5], 1):
        score   = doc.get("score", 0)
        content = doc.get("content", "")
        source  = doc.get("metadata", {}).get("source", "").split("/")[-1]
        tags    = doc.get("metadata", {}).get("tags", "")

        parts.append(
            f"[Source {i} | score={score:.2f} | {source} | tags={tags}]\n"
            f"{content[:400]}"
        )

    return "\n\n---\n\n".join(parts)


def _detect_contradictions(docs: list) -> list:
    """
    Détecte les contradictions simples entre sources (délais, prix).
    Retourne une liste de conflits détectés.
    """
    contradictions = []

    # Cherche des chiffres liés aux délais
    delay_pattern = re.compile(r'(\d+)\s*(?:à|-)\s*(\d+)\s*(?:jours|days|أيام)', re.IGNORECASE)

    all_delays = []
    for doc in docs:
        content = doc.get("content", "")
        matches = delay_pattern.findall(content)
        all_delays.extend(matches)

    # Si des délais très différents existent → possible contradiction
    if len(all_delays) > 1:
        mins = [int(m[0]) for m in all_delays]
        maxs = [int(m[1]) for m in all_delays]
        if max(mins) - min(mins) > 3 or max(maxs) - min(maxs) > 5:
            contradictions.append(
                f"Délais potentiellement incohérents entre sources: {all_delays}"
            )

    return contradictions


def synthesize_answer(question: str,
                       docs: list,
                       lang: str = "french",
                       tone: str = "") -> dict:
    """
    Synthèse multi-documents pour générer une réponse cohérente.
    Adapté depuis Portalyze FivePAgent.generate_report()

    Args:
        question : question du client
        docs     : liste de documents récupérés par ChromaDB
        lang     : langue de réponse (french/english/arabic)
        tone     : instruction de ton depuis analyze_sentiment()

    Returns:
        dict {answer, topic, contradictions, sources_used}
    """
    if not docs:
        return {
            "answer":        "Information non disponible. Contactez support@hoodiewear.com",
            "topic":         "default",
            "contradictions": [],
            "sources_used":  0,
        }

    topic           = _detect_topic(question)
    context         = _format_multi_context(docs)
    lang_label      = LANG_LABELS.get(lang, "français")
    contradictions  = _detect_contradictions(docs)
    template        = SYNTHESIS_TEMPLATES.get(topic, SYNTHESIS_TEMPLATES["default"])

    # Ajoute instruction de ton si sentiment détecté
    tone_prefix = ""
    if tone:
        tone_prefix = f"\n\nINSTRUCTION DE TON : {tone[:200]}\n"

    prompt = tone_prefix + template.format(
        context=context,
        question=question,
        lang=lang_label
    )

    # Avertissement contradictions
    if contradictions:
        prompt += f"\n\n⚠️ ATTENTION : Contradictions détectées entre sources : {contradictions}. Utilise les faits les plus récents ou les plus fréquents."

    try:
        response = client.chat.completions.create(
            model=MODEL_SYNTH,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.25,
            max_tokens=400,
        )
        answer = response.choices[0].message.content.strip()

        # Nettoyage artefacts LLM
        for phrase in ["Bien sûr,", "Certainement,", "Voici la réponse :",
                       "Je vais vous expliquer", "Absolutely,", "Sure,"]:
            answer = answer.replace(phrase, "").strip()

    except Exception as e:
        print(f"❌ Erreur synthèse: {e}")
        answer = "Information non disponible. Contactez support@hoodiewear.com 😊"

    return {
        "answer":         answer,
        "topic":          topic,
        "contradictions": contradictions,
        "sources_used":   len(docs),
    }


def synthesize_stream(question: str,
                       docs: list,
                       lang: str = "french",
                       tone: str = ""):
    """
    Version streaming de synthesize_answer.
    Yield des tokens un par un pour st.write_stream().
    """
    if not docs:
        yield "Information non disponible. Contactez **support@hoodiewear.com** 😊"
        return

    topic      = _detect_topic(question)
    context    = _format_multi_context(docs)
    lang_label = LANG_LABELS.get(lang, "français")
    template   = SYNTHESIS_TEMPLATES.get(topic, SYNTHESIS_TEMPLATES["default"])

    tone_prefix = f"\n\nINSTRUCTION DE TON : {tone[:200]}\n" if tone else ""
    prompt = tone_prefix + template.format(
        context=context, question=question, lang=lang_label
    )

    try:
        stream = client.chat.completions.create(
            model=MODEL_SYNTH,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.25,
            max_tokens=400,
            stream=True,
        )
        for chunk in stream:
            token = chunk.choices[0].delta.content
            if token:
                yield token
    except Exception as e:
        print(f"❌ Erreur stream synthèse: {e}")
        yield "Information non disponible. Contactez **support@hoodiewear.com** 😊"


# ── Test ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    fake_docs = [
        {
            "score": 0.82,
            "content": "Livraison Tunisie : 3 à 5 jours ouvrés via transporteur partenaire.",
            "metadata": {"source": "faq_livraison.json", "tags": "livraison"}
        },
        {
            "score": 0.71,
            "content": "Les colis sont expédiés sous 24h après validation de la commande.",
            "metadata": {"source": "faq_commandes.json", "tags": "commande,livraison"}
        }
    ]
    result = synthesize_answer(
        question="Combien de temps pour recevoir ma commande en Tunisie ?",
        docs=fake_docs,
        lang="french"
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))