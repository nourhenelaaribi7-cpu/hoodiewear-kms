"""
Pipeline RAG optimisé — gestion tokens Groq
- Cache réponses fréquentes
- Suggestions sans LLM (règles)
- Modèle léger pour tâches secondaires
- Compteur tokens avec alerte
"""
import os
import json
import hashlib
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
from src.retriever import retrieve_relevant_docs, format_context
from src.sentiment import analyze_sentiment, get_escalation_needed

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── Modèles disponibles ────────────────────────────────────────────────────────
MODEL_MAIN  = "llama-3.3-70b-versatile"   # Réponses principales (qualité)
MODEL_LIGHT = "llama-3.1-8b-instant"      # Tâches légères (suggestions, éval)
# MODEL_LIGHT tokens/day : 500,000 (5x plus généreux !)

# ── Fichiers ───────────────────────────────────────────────────────────────────
CACHE_FILE        = "data/response_cache.json"
TOKEN_TRACKER     = "data/token_usage.json"
GAP_FILE          = "data/potential_gaps_realtime.json"
RAG_LACUNE_SEUIL  = 0.40
TOKEN_DAILY_LIMIT = 95000   # Alerte à 95% de la limite (100k)

# ── Prompts système ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Tu es un assistant du service client de HoodieWear, boutique streetwear.
Règles :
1. Réponds UNIQUEMENT depuis le contexte fourni.
2. Si info absente : redirige vers support@hoodiewear.com.
3. Utilise l'historique pour la cohérence.
4. Respecte le ton demandé.
5. Réponds toujours dans la langue de la question."""

DEFAULT_RESPONSES = {
    "french":  "Information non disponible dans notre base. Contactez **support@hoodiewear.com** 😊",
    "english": "Information not available. Please contact **support@hoodiewear.com** 😊",
    "arabic":  "المعلومات غير متوفرة. تواصل مع **support@hoodiewear.com** 😊"
}

ESCALATION_MESSAGE = {
    "french":  "⚠️ Problème sérieux détecté. Contactez **support@hoodiewear.com** ou **+216 XX XXX XXX**. Priorité absolue. 🙏",
    "english": "⚠️ Serious issue detected. Contact **support@hoodiewear.com** immediately. 🙏",
    "arabic":  "⚠️ مشكلة جدية. تواصل مع **support@hoodiewear.com** فوراً. 🙏"
}

# ── Suggestions par règles (ZERO token) ───────────────────────────────────────
SUGGESTIONS_BY_TOPIC = {
    "livraison": {
        "french":  ["Quels sont les frais de livraison ?", "Puis-je changer mon adresse de livraison ?", "Comment suivre mon colis ?"],
        "english": ["What are the shipping costs?", "Can I change my delivery address?", "How do I track my package?"],
        "arabic":  ["ما هي تكاليف الشحن؟", "هل يمكنني تغيير عنوان التسليم؟", "كيف أتتبع طردي؟"]
    },
    "retour": {
        "french":  ["Combien de temps pour le remboursement ?", "Les retours sont-ils gratuits ?", "Puis-je échanger au lieu de retourner ?"],
        "english": ["How long does the refund take?", "Are returns free?", "Can I exchange instead of returning?"],
        "arabic":  ["كم يستغرق الاسترداد؟", "هل الإرجاع مجاني؟", "هل يمكنني الاستبدال بدلاً من الإرجاع؟"]
    },
    "paiement": {
        "french":  ["Le paiement à la livraison est-il disponible ?", "Comment obtenir un remboursement ?", "Mes données bancaires sont-elles sécurisées ?"],
        "english": ["Is cash on delivery available?", "How do I get a refund?", "Is my payment data secure?"],
        "arabic":  ["هل الدفع عند الاستلام متاح؟", "كيف أحصل على استرداد؟", "هل بياناتي المصرفية آمنة؟"]
    },
    "taille": {
        "french":  ["Comment mesurer ma taille correctement ?", "Puis-je échanger si la taille ne convient pas ?", "Les hoodies rétrécissent-ils au lavage ?"],
        "english": ["How do I measure my size correctly?", "Can I exchange if the size doesn't fit?", "Do hoodies shrink when washed?"],
        "arabic":  ["كيف أقيس مقاسي بشكل صحيح؟", "هل يمكنني الاستبدال إذا لم يناسبني المقاس؟", "هل تنكمش الهوديات عند الغسيل؟"]
    },
    "commande": {
        "french":  ["Puis-je modifier ma commande ?", "Comment annuler ma commande ?", "Où est ma commande actuellement ?"],
        "english": ["Can I modify my order?", "How do I cancel my order?", "Where is my order now?"],
        "arabic":  ["هل يمكنني تعديل طلبيتي؟", "كيف أُلغي طلبيتي؟", "أين طلبيتي الآن؟"]
    },
    "compte": {
        "french":  ["Comment changer mon email ?", "Comment supprimer mon compte ?", "Comment voir mon historique de commandes ?"],
        "english": ["How do I change my email?", "How do I delete my account?", "How do I see my order history?"],
        "arabic":  ["كيف أغير بريدي الإلكتروني؟", "كيف أحذف حسابي؟", "كيف أرى تاريخ طلباتي؟"]
    },
    "entretien": {
        "french":  ["Puis-je mettre mon hoodie au sèche-linge ?", "Comment éviter que les couleurs ne déteintent ?", "À quelle fréquence laver mon hoodie ?"],
        "english": ["Can I put my hoodie in the dryer?", "How do I prevent colors from fading?", "How often should I wash my hoodie?"],
        "arabic":  ["هل يمكنني وضع هوديتي في المجفف؟", "كيف أمنع بهتان الألوان؟", "كم مرة أغسل هوديتي؟"]
    },
    "default": {
        "french":  ["Comment contacter le service client ?", "Où est ma commande ?", "Comment retourner un article ?"],
        "english": ["How do I contact customer service?", "Where is my order?", "How do I return an item?"],
        "arabic":  ["كيف أتواصل مع خدمة العملاء؟", "أين طلبيتي؟", "كيف أُرجع منتجاً؟"]
    }
}

TOPIC_KEYWORDS = {
    "livraison": ["livraison", "délai", "expédition", "colis", "delivery", "ship", "شحن", "تسليم"],
    "retour":    ["retour", "rembours", "échange", "return", "refund", "إرجاع", "استرداد"],
    "paiement":  ["paiement", "carte", "paypal", "virement", "payment", "pay", "دفع", "بطاقة"],
    "taille":    ["taille", "tailles", "size", "xl", "xxl", "xs", "mesure", "مقاس"],
    "commande":  ["commande", "commander", "annuler", "order", "cancel", "طلب", "إلغاء"],
    "compte":    ["compte", "mot de passe", "connexion", "account", "password", "حساب", "كلمة مرور"],
    "entretien": ["laver", "lavage", "entretien", "wash", "care", "غسيل", "عناية"]
}


def detect_topic(question: str, sources: list) -> str:
    """Détecte le topic de la question pour les suggestions sans LLM"""
    text = question.lower()

    # Cherche dans les tags des sources en premier
    for src in sources:
        tags = src.get("metadata", {}).get("tags", "").lower()
        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(kw in tags for kw in keywords):
                return topic

    # Cherche dans la question
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return topic

    return "default"


# ── Gestionnaire de tokens ─────────────────────────────────────────────────────
def _load_token_usage() -> dict:
    if not os.path.exists(TOKEN_TRACKER):
        return {"date": datetime.now().strftime("%Y-%m-%d"), "tokens_used": 0}
    try:
        with open(TOKEN_TRACKER, "r") as f:
            data = json.load(f)
        # Reset si nouveau jour
        if data.get("date") != datetime.now().strftime("%Y-%m-%d"):
            return {"date": datetime.now().strftime("%Y-%m-%d"), "tokens_used": 0}
        return data
    except Exception:
        return {"date": datetime.now().strftime("%Y-%m-%d"), "tokens_used": 0}


def _save_token_usage(tokens_used: int):
    os.makedirs("data", exist_ok=True)
    usage = _load_token_usage()
    usage["tokens_used"] += tokens_used
    with open(TOKEN_TRACKER, "w") as f:
        json.dump(usage, f)


def get_token_usage() -> dict:
    """Retourne l'usage actuel des tokens (pour l'affichage)"""
    usage = _load_token_usage()
    used  = usage.get("tokens_used", 0)
    return {
        "used":       used,
        "limit":      100000,
        "remaining":  100000 - used,
        "percent":    round(used / 100000 * 100, 1),
        "critical":   used >= TOKEN_DAILY_LIMIT
    }


def _is_near_limit() -> bool:
    """True si on est à 95% de la limite quotidienne"""
    usage = _load_token_usage()
    return usage.get("tokens_used", 0) >= TOKEN_DAILY_LIMIT


# ── Cache des réponses ─────────────────────────────────────────────────────────
def _get_cache_key(question: str, lang: str) -> str:
    return hashlib.md5(f"{question.lower().strip()}_{lang}".encode()).hexdigest()


def _load_cache() -> dict:
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else {}
    except Exception:
        return {}


def _save_to_cache(key: str, answer: str, sources: list, lang: str):
    """Cache uniquement les réponses avec bon score"""
    os.makedirs("data", exist_ok=True)
    cache = _load_cache()
    cache[key] = {
        "answer":    answer,
        "lang":      lang,
        "cached_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "hits":      0
    }
    # Garde max 200 entrées
    if len(cache) > 200:
        oldest = sorted(cache.items(), key=lambda x: x[1].get("cached_at", ""))[0][0]
        del cache[oldest]
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _get_from_cache(key: str) -> dict | None:
    cache = _load_cache()
    if key in cache:
        # Incrémente le compteur de hits
        cache[key]["hits"] = cache[key].get("hits", 0) + 1
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        return cache[key]
    return None


# ── Tracking lacunes ───────────────────────────────────────────────────────────
def _track_potential_gap(question: str, avg_score: float,
                         answer: str, lang: str):
    if avg_score >= RAG_LACUNE_SEUIL:
        return
    os.makedirs("data", exist_ok=True)
    existing = []
    if os.path.exists(GAP_FILE):
        try:
            with open(GAP_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                existing = json.loads(content) if content else []
        except Exception:
            existing = []

    if question.lower() in {e["question"].lower() for e in existing}:
        return

    existing.append({
        "question":  question,
        "score_rag": round(avg_score, 3),
        "answer":    answer[:150],
        "langue":    lang,
        "date":      datetime.now().strftime("%Y-%m-%d %H:%M"),
        "statut":    "non_traité"
    })
    with open(GAP_FILE, "w", encoding="utf-8") as f:
        json.dump(existing[-100:], f, ensure_ascii=False, indent=2)


# ── Détection langue ───────────────────────────────────────────────────────────
def detect_language(text: str) -> str:
    arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    if arabic_chars > 2:
        return "arabic"

    text_lower = text.lower()
    words      = text_lower.split()

    french_words = {
        "je", "j'ai", "j'", "mon", "ma", "mes", "les", "des", "est",
        "sont", "vous", "nous", "tu", "il", "elle", "ils", "elles",
        "pour", "dans", "avec", "sur", "par", "que", "qui", "quoi",
        "une", "pas", "plus", "très", "aussi", "mais", "ou", "et",
        "pouvez", "puis", "peut", "faire", "avoir", "être", "aller",
        "livraison", "commande", "retour", "taille", "paiement",
        "délai", "bonjour", "merci", "remboursement", "annuler",
        "suivre", "recevoir", "envoyer", "contacter",
        "comment", "quels", "quelle", "quand", "pourquoi", "où", "quel",
        "combien", "est-ce", "s'il", "votre", "notre", "svp", "stp"
    }
    english_words = {
        "i", "my", "you", "your", "we", "our", "they", "their",
        "it", "its", "he", "she",
        "is", "are", "was", "were", "have", "has", "do", "does",
        "can", "could", "would", "should", "will", "get", "want",
        "need", "like", "know",
        "the", "a", "an", "to", "of", "in", "on", "at", "for",
        "with", "from", "by", "and", "or", "but", "not",
        "order", "delivery", "return", "size", "payment", "track",
        "ship", "shipping", "refund", "cancel", "help", "please",
        "hello", "hi", "thank", "thanks",
        "what", "how", "when", "where", "why", "which", "who"
    }

    fr_score = sum(1 for w in words if w in french_words)
    en_score = sum(1 for w in words if w in english_words)

    french_accents = set("àâäéèêëîïôöùûüçœæ")
    fr_score += sum(0.5 for c in text_lower if c in french_accents)

    if en_score > fr_score and en_score >= 2:
        return "english"
    return "french"


def get_language_instruction(lang: str) -> str:
    return {
        "arabic":  "IMPORTANT : Tu DOIS répondre UNIQUEMENT en arabe. Aucun mot en français ou anglais.",
        "english": "IMPORTANT : You MUST answer ONLY in English. No French words.",
        "french":  "IMPORTANT : Tu DOIS répondre UNIQUEMENT en français. Aucun mot en anglais."
    }.get(lang, "IMPORTANT : Tu DOIS répondre UNIQUEMENT en français.")


# ── Construction messages ──────────────────────────────────────────────────────
def build_messages(question: str, context: str, chat_history: list,
                   lang: str, tone_instruction: str) -> list:
    full_system = (
        SYSTEM_PROMPT
        + f"\n\n🎭 TON : {tone_instruction}"
        + f"\n\n🌍 {get_language_instruction(lang)}"
    )
    messages = [{"role": "system", "content": full_system}]
    if chat_history:
        for msg in chat_history[-4:]:   # Réduit de 6 à 4 pour économiser
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({
        "role": "user",
        "content": f"Contexte HoodieWear :\n---\n{context[:2000]}\n---\nQuestion : {question}"
        # Limite le contexte à 2000 chars pour économiser
    })
    return messages


# ── Appels LLM ─────────────────────────────────────────────────────────────────
def call_groq_llm(question: str, context: str, chat_history: list = None,
                  lang: str = "french", tone_instruction: str = "") -> str:
    messages = build_messages(question, context, chat_history or [],
                               lang, tone_instruction)
    response = client.chat.completions.create(
        model=MODEL_MAIN,
        messages=messages,
        temperature=0.3,
        max_tokens=400   # Réduit de 500 à 400
    )
    # Track tokens
    usage = response.usage
    if usage:
        _save_token_usage(usage.total_tokens)
        print(f"🔢 Tokens utilisés : {usage.total_tokens} | Total jour : {get_token_usage()['used']}")

    return response.choices[0].message.content.strip()


def call_groq_llm_stream(question: str, context: str, chat_history: list = None,
                         lang: str = "french", tone_instruction: str = ""):
    """Streaming avec modèle principal"""
    messages = build_messages(question, context, chat_history or [],
                               lang, tone_instruction)
    stream = client.chat.completions.create(
        model=MODEL_MAIN,
        messages=messages,
        temperature=0.3,
        max_tokens=400,
        stream=True
    )
    for chunk in stream:
        token = chunk.choices[0].delta.content
        if token is not None:
            yield token


# ── Suggestions SANS LLM (règles) ─────────────────────────────────────────────
def suggest_followup_questions(question: str, answer: str,
                               lang: str = "french",
                               sources: list = None) -> list:
    """
    Génère des suggestions PAR RÈGLES — zéro appel LLM, zéro token !
    Détecte le topic depuis la question + les sources.
    """
    topic       = detect_topic(question, sources or [])
    suggestions = SUGGESTIONS_BY_TOPIC.get(topic, SUGGESTIONS_BY_TOPIC["default"])
    result      = suggestions.get(lang, suggestions.get("french", []))

    print(f"💡 Suggestions topic='{topic}' lang='{lang}': {result}")
    return result


# ── Pipelines RAG ──────────────────────────────────────────────────────────────
def answer_question_stream(question: str, chat_history: list = None):
    """Pipeline RAG avec streaming + cache + gestion tokens"""

    lang      = detect_language(question)
    sentiment = analyze_sentiment(question)

    # Escalade
    if get_escalation_needed(sentiment["sentiment"],
                             sentiment["scores"].get("frustré", 0)):
        msg = ESCALATION_MESSAGE.get(lang, ESCALATION_MESSAGE["french"])
        return {
            "stream": iter(msg.split(" ")),
            "metadata": {
                "sources": [], "sentiment": sentiment, "language": lang,
                "escalation": True, "suggestions": [], "from_cache": False
            }
        }

    # Vérifie le cache
    cache_key    = _get_cache_key(question, lang)
    cached       = _get_from_cache(cache_key)
    if cached:
        print(f"✅ Cache hit ! (économie tokens)")
        cached_answer = cached["answer"]

        def cached_stream():
            for word in cached_answer.split(" "):
                yield word + " "

        return {
            "stream": cached_stream(),
            "metadata": {
                "sources": [], "sentiment": sentiment, "language": lang,
                "escalation": False,
                "suggestions": suggest_followup_questions(question, cached_answer, lang),
                "from_cache": True
            }
        }

    # Alerte limite tokens
    if _is_near_limit():
        fallback = DEFAULT_RESPONSES.get(lang, DEFAULT_RESPONSES["french"])
        fallback += "\n\n⚠️ Service temporairement limité. Veuillez réessayer demain."

        def limit_stream():
            for word in fallback.split(" "):
                yield word + " "

        return {
            "stream": limit_stream(),
            "metadata": {
                "sources": [], "sentiment": sentiment, "language": lang,
                "escalation": False, "suggestions": [], "from_cache": False
            }
        }

    # Recherche sémantique
    retrieved = retrieve_relevant_docs(question, n_results=5)
    good_docs = [d for d in retrieved if d["score"] >= 0.3]
    avg_score = sum(d["score"] for d in good_docs) / len(good_docs) if good_docs else 0

    if not good_docs:
        fallback = DEFAULT_RESPONSES.get(lang, DEFAULT_RESPONSES["french"])
        _track_potential_gap(question, 0.0, fallback, lang)

        def fallback_stream():
            for word in fallback.split(" "):
                yield word + " "

        return {
            "stream": fallback_stream(),
            "metadata": {
                "sources": [], "sentiment": sentiment, "language": lang,
                "escalation": False,
                "suggestions": suggest_followup_questions(question, "", lang),
                "from_cache": False
            }
        }

    context      = format_context(good_docs)
    token_stream = call_groq_llm_stream(
        question=question, context=context,
        chat_history=chat_history, lang=lang,
        tone_instruction=sentiment["tone_instruction"]
    )

    if avg_score < RAG_LACUNE_SEUIL:
        _track_potential_gap(question, avg_score, "", lang)

    return {
        "stream": token_stream,
        "metadata": {
            "sources": good_docs, "sentiment": sentiment, "language": lang,
            "escalation": False,
            "suggestions": suggest_followup_questions(question, "", lang, good_docs),
            "from_cache": False
        }
    }


def answer_question(question: str, chat_history: list = None):
    """Pipeline RAG sans streaming + cache + gestion tokens"""

    lang      = detect_language(question)
    sentiment = analyze_sentiment(question)

    # Escalade
    if get_escalation_needed(sentiment["sentiment"],
                             sentiment["scores"].get("frustré", 0)):
        return {
            "answer":      ESCALATION_MESSAGE.get(lang, ESCALATION_MESSAGE["french"]),
            "sources":     [], "context_used": "", "language": lang,
            "sentiment":   sentiment, "suggestions": [],
            "escalation":  True, "from_cache": False
        }

    # Cache
    cache_key = _get_cache_key(question, lang)
    cached    = _get_from_cache(cache_key)
    if cached:
        print(f"✅ Cache hit !")
        return {
            "answer":      cached["answer"],
            "sources":     [], "context_used": "", "language": lang,
            "sentiment":   sentiment,
            "suggestions": suggest_followup_questions(question, cached["answer"], lang),
            "escalation":  False, "from_cache": True
        }

    # Limite tokens
    if _is_near_limit():
        fallback = DEFAULT_RESPONSES.get(lang, DEFAULT_RESPONSES["french"])
        return {
            "answer":      fallback + "\n\n⚠️ Limite quotidienne atteinte. Réessayez demain.",
            "sources":     [], "context_used": "", "language": lang,
            "sentiment":   sentiment, "suggestions": [],
            "escalation":  False, "from_cache": False
        }

    # Recherche
    retrieved = retrieve_relevant_docs(question, n_results=5)
    good_docs = [d for d in retrieved if d["score"] >= 0.3]
    avg_score = sum(d["score"] for d in good_docs) / len(good_docs) if good_docs else 0

    if not good_docs:
        fallback = DEFAULT_RESPONSES.get(lang, DEFAULT_RESPONSES["french"])
        _track_potential_gap(question, 0.0, fallback, lang)
        return {
            "answer":      fallback,
            "sources":     [], "context_used": "", "language": lang,
            "sentiment":   sentiment,
            "suggestions": suggest_followup_questions(question, fallback, lang),
            "escalation":  False, "from_cache": False
        }

    context = format_context(good_docs)
    try:
        answer = call_groq_llm(
            question=question, context=context,
            chat_history=chat_history, lang=lang,
            tone_instruction=sentiment["tone_instruction"]
        )
        # Met en cache si bon score
        if avg_score >= 0.5:
            _save_to_cache(cache_key, answer, good_docs, lang)

    except Exception as e:
        print(f"❌ Erreur Groq : {e}")
        answer = DEFAULT_RESPONSES.get(lang, DEFAULT_RESPONSES["french"])

    if avg_score < RAG_LACUNE_SEUIL:
        _track_potential_gap(question, avg_score, answer, lang)

    return {
        "answer":      answer,
        "sources":     good_docs,
        "context_used": context,
        "language":    lang,
        "sentiment":   sentiment,
        "suggestions": suggest_followup_questions(question, answer, lang, good_docs),
        "escalation":  False,
        "from_cache":  False
    }