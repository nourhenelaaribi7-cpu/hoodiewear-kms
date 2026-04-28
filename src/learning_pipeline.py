# src/learning_pipeline.py
"""
Continuous Learning RAG — Pipeline d'apprentissage automatique
==============================================================
CORRECTIONS v3 :
  1. _get_rag_score_honest()     : exclut le doc appris pour éviter les faux positifs
  2. _is_already_indexed()       : vérifie si une question similaire est déjà indexée
                                   avant d'ajouter (évite la pollution ChromaDB)
  3. _validate_generated_response() : validation LLM des faits avant indexation
  4. _safe_json_write()          : écriture thread-safe via fichier temporaire
  5. auto_learn_from_feedback()  : intègre toutes les corrections ci-dessus

Flux complet :
    Feedback 👎
        ↓
    [0] Déduplication — question déjà indexée ? → skip
        ↓
    [1] Détection automatique de la lacune
        ↓
    [2] Génération d'une réponse experte (LLM)
        ↓
    [2b] Validation des faits (LLM-as-judge)
        ↓
    [3] Indexation immédiate dans ChromaDB
        ↓
    [4] Validation : score RAG honnête (exclut le nouveau doc)
        ↓
    [5a] Score amélioré → ✅ Gap résolu
    [5b] Score insuffisant → 🔄 Re-génération (prompt renforcé)
        ↓
    [6] Mise à jour du Learning Log (traçabilité complète)
"""

import os
import json
import time
import hashlib
import threading
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── Fichiers ────────────────────────────────────────────────────────────────────
LEARNING_LOG_FILE   = "data/learning_log.json"
LEARNED_FAQ_FILE    = "data/raw/faq_auto_learned.json"
PENDING_GAPS_FILE   = "data/potential_gaps_realtime.json"
FEEDBACK_FILE       = "data/feedback.json"

# ── Seuils ──────────────────────────────────────────────────────────────────────
SCORE_TARGET        = 0.55   # Score RAG cible après apprentissage
SCORE_MIN_TRIGGER   = 0.45   # En dessous → on déclenche l'apprentissage
MAX_ATTEMPTS        = 2      # Nombre max de tentatives de génération
MIN_RESPONSE_LEN    = 30     # Longueur minimale d'une réponse valide
DEDUP_THRESHOLD     = 0.82   # Seuil de similarité pour la déduplication

# ── Modèle ──────────────────────────────────────────────────────────────────────
MODEL = "llama-3.3-70b-versatile"

# ── Lock thread-safe pour les écritures JSON ────────────────────────────────────
_json_lock = threading.Lock()

# ── Faits HoodieWear pour la validation ────────────────────────────────────────
HOODIEWEAR_FACTS = """
Faits HoodieWear vérifiés :
- Livraison Tunisie : 3-5 jours (jamais moins de 2 jours, jamais plus de 7)
- Livraison Europe : 5-10 jours
- Livraison internationale : 10-15 jours
- Retours : 30 jours maximum (jamais 15 jours, jamais 60 jours)
- Paiement à la livraison : supplément 3 DT (pas 5 DT, pas gratuit)
- Email support : support@hoodiewear.com (pas d'autre email)
- Tailles disponibles : XS, S, M, L, XL, XXL
- Remboursement après retour : 5-7 jours ouvrés
- Annulation gratuite : dans les 24h après commande
"""


# ══════════════════════════════════════════════════════════════════════════════
# 0. ÉCRITURE JSON THREAD-SAFE
# ══════════════════════════════════════════════════════════════════════════════

def _safe_json_write(filepath: str, data: list):
    """
    Écriture thread-safe dans un fichier JSON via fichier temporaire.
    Évite la corruption en cas d'écritures simultanées.
    """
    with _json_lock:
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
        tmp = filepath + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, filepath)   # Opération atomique sur le filesystem
        except Exception as e:
            # Nettoyage du fichier temporaire en cas d'erreur
            if os.path.exists(tmp):
                os.remove(tmp)
            raise e


def _safe_json_append(filepath: str, new_entry: dict, max_entries: int = 500):
    """
    Lecture + ajout + écriture thread-safe dans un fichier JSON.
    """
    with _json_lock:
        existing = []
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    existing = json.loads(f.read().strip() or "[]")
            except Exception:
                existing = []

        existing.append(new_entry)
        # Limite la taille du fichier
        if max_entries and len(existing) > max_entries:
            existing = existing[-max_entries:]

        tmp = filepath + ".tmp"
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
            os.replace(tmp, filepath)
        except Exception as e:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise e


# ══════════════════════════════════════════════════════════════════════════════
# 1. LOGGING DU SYSTÈME D'APPRENTISSAGE
# ══════════════════════════════════════════════════════════════════════════════

def load_learning_log() -> list:
    if not os.path.exists(LEARNING_LOG_FILE):
        return []
    try:
        with open(LEARNING_LOG_FILE, "r", encoding="utf-8") as f:
            return json.loads(f.read().strip() or "[]")
    except Exception:
        return []


def save_learning_event(event: dict):
    """Enregistre chaque événement d'apprentissage pour traçabilité."""
    os.makedirs("data", exist_ok=True)
    event_with_ts = {**event, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    _safe_json_append(LEARNING_LOG_FILE, event_with_ts, max_entries=500)


def get_learning_stats() -> dict:
    """
    Retourne les statistiques complètes du système d'apprentissage.
    """
    log = load_learning_log()

    if not log:
        return {
            "total_events":       0,
            "total_learned":      0,
            "success_rate":       0.0,
            "avg_score_before":   0.0,
            "avg_score_after":    0.0,
            "avg_improvement":    0.0,
            "avg_time_seconds":   0.0,
            "last_learning":      None,
            "topics_learned":     {},
            "evolution_by_day":   []
        }

    learned_events = [e for e in log if e.get("status") == "success"]
    failed_events  = [e for e in log if e.get("status") == "failed"]

    scores_before = [e.get("score_before", 0) for e in learned_events if e.get("score_before")]
    scores_after  = [e.get("score_after", 0)  for e in learned_events if e.get("score_after")]
    times         = [e.get("duration_seconds", 0) for e in learned_events]

    avg_before = round(sum(scores_before) / len(scores_before), 3) if scores_before else 0
    avg_after  = round(sum(scores_after)  / len(scores_after),  3) if scores_after  else 0

    topics = {}
    for e in learned_events:
        t = e.get("topic", "autre")
        topics[t] = topics.get(t, 0) + 1

    by_day = {}
    for e in log:
        day = e.get("timestamp", "")[:10]
        if day not in by_day:
            by_day[day] = {"date": day, "learned": 0, "failed": 0, "avg_improvement": []}
        if e.get("status") == "success":
            by_day[day]["learned"] += 1
            imp = e.get("score_after", 0) - e.get("score_before", 0)
            by_day[day]["avg_improvement"].append(imp)
        else:
            by_day[day]["failed"] += 1

    evolution = []
    for day, data in sorted(by_day.items()):
        imps = data["avg_improvement"]
        evolution.append({
            "date":            data["date"],
            "learned":         data["learned"],
            "failed":          data["failed"],
            "avg_improvement": round(sum(imps) / len(imps), 3) if imps else 0
        })

    total = len(learned_events) + len(failed_events)
    return {
        "total_events":     len(log),
        "total_learned":    len(learned_events),
        "total_failed":     len(failed_events),
        "success_rate":     round(len(learned_events) / total * 100, 1) if total > 0 else 0,
        "avg_score_before": avg_before,
        "avg_score_after":  avg_after,
        "avg_improvement":  round(avg_after - avg_before, 3),
        "avg_time_seconds": round(sum(times) / len(times), 1) if times else 0,
        "last_learning":    log[-1].get("timestamp") if log else None,
        "topics_learned":   topics,
        "evolution_by_day": evolution
    }


# ══════════════════════════════════════════════════════════════════════════════
# 2. DÉTECTION DE TOPIC / LANGUE
# ══════════════════════════════════════════════════════════════════════════════

TOPIC_KEYWORDS = {
    "livraison":     ["livraison", "livrer", "délai", "expédition", "colis",
                      "delivery", "ship", "shipping", "شحن", "تسليم", "توصيل"],
    "retour":        ["retour", "rembours", "échange", "return", "refund",
                      "إرجاع", "استرداد", "ارجاع"],
    "paiement":      ["paiement", "carte", "paypal", "virement", "payment",
                      "pay", "دفع", "بطاقة", "فلوس"],
    "taille":        ["taille", "size", "xl", "xxl", "xs", "mesure",
                      "guide", "مقاس", "قياس"],
    "commande":      ["commande", "commander", "annuler", "order", "cancel",
                      "tracking", "طلب", "إلغاء", "تتبع"],
    "entretien":     ["laver", "lavage", "entretien", "wash", "care",
                      "sécher", "repasser", "غسيل", "عناية"],
    "compte":        ["compte", "mot de passe", "connexion", "account",
                      "password", "login", "حساب", "كلمة مرور"],
    "produit":       ["hoodie", "qualité", "couleur", "défaut", "couture",
                      "tissu", "quality", "defect", "جودة", "خامة"],
    "international": ["international", "europe", "france", "étranger",
                      "abroad", "خارج", "دولي"],
}

def detect_topic(question: str) -> str:
    q = question.lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return topic
    return "general"


def detect_language(text: str) -> str:
    arabic = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    if arabic > 2:
        return "ar"
    eng_words = {"what", "how", "when", "where", "can", "is", "my", "the",
                 "i", "do", "does", "help", "order", "delivery", "return"}
    if len(set(text.lower().split()) & eng_words) >= 2:
        return "en"
    return "fr"


# ══════════════════════════════════════════════════════════════════════════════
# 3. NOUVEAU — DÉDUPLICATION AVANT INDEXATION
# ══════════════════════════════════════════════════════════════════════════════

def _is_already_indexed(question: str, threshold: float = DEDUP_THRESHOLD) -> bool:
    """
    Vérifie si une question très similaire est déjà présente dans ChromaDB.
    Évite la pollution progressive de la base avec des doublons.

    Returns:
        True si une entrée similaire existe déjà (score >= threshold)
    """
    from src.indexer import get_collection
    collection = get_collection()
    try:
        results = collection.query(
            query_texts=[question],
            n_results=1,
            include=["distances"]
        )
        if results["distances"] and results["distances"][0]:
            score = round(1 - results["distances"][0][0], 3)
            return score >= threshold
    except Exception:
        pass
    return False


# ══════════════════════════════════════════════════════════════════════════════
# 4. NOUVEAU — VALIDATION LLM DES FAITS AVANT INDEXATION
# ══════════════════════════════════════════════════════════════════════════════

def _validate_generated_response(question: str, response: str) -> dict:
    """
    Vérifie que la réponse générée est cohérente avec les faits HoodieWear
    avant de l'indexer dans ChromaDB.

    Évite l'indexation d'hallucinations (délais inventés, prix erronés, etc.)

    Returns:
        dict {"valid": bool, "issues": list[str]}
    """
    validation_prompt = f"""Tu es un validateur qualité pour HoodieWear.

Vérifie si cette réponse contient des informations CORRECTES selon les faits officiels.

{HOODIEWEAR_FACTS}

Question client : "{question}"
Réponse à valider : "{response}"

Instructions :
- Si la réponse contient des délais, prix ou procédures qui contredisent les faits ci-dessus → invalide
- Si la réponse est vague mais correcte → valide
- Si tu n'es pas sûr → valide (bénéfice du doute)

Réponds UNIQUEMENT avec ce JSON (rien d'autre) :
{{"valid": true, "issues": []}}
ou
{{"valid": false, "issues": ["description du problème détecté"]}}"""

    try:
        result = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": validation_prompt}],
            temperature=0.0,
            max_tokens=120
        )
        raw   = result.choices[0].message.content.strip()
        import re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            return {
                "valid":  bool(parsed.get("valid", True)),
                "issues": parsed.get("issues", [])
            }
    except Exception as e:
        print(f"   ⚠️  Validation LLM échouée : {e} — on laisse passer (permissif)")

    # Fallback permissif : en cas d'erreur, on autorise
    return {"valid": True, "issues": []}


# ══════════════════════════════════════════════════════════════════════════════
# 5. NOUVEAU — SCORE RAG HONNÊTE (EXCLUT LE DOC APPRIS)
# ══════════════════════════════════════════════════════════════════════════════

def _get_rag_score_honest(question: str, exclude_doc_id: str = None) -> float:
    """
    Score RAG honnête : exclut le document qu'on vient d'indexer.

    Sans cette exclusion, ChromaDB retourne souvent le nouveau doc en
    premier (score élevé car il contient exactement la question) ce qui
    crée un faux positif systématique.

    Args:
        question       : question à tester
        exclude_doc_id : ID du document à exclure (celui qu'on vient d'indexer)

    Returns:
        float : score RAG moyen sur les 3 meilleurs docs (hors nouveau doc)
    """
    from src.retriever import retrieve_relevant_docs
    try:
        # On demande plus de résultats pour compenser l'exclusion
        docs = retrieve_relevant_docs(question, n_results=5, min_score=0.0)

        # Exclure le doc appris si son ID est fourni
        if exclude_doc_id:
            docs = [d for d in docs
                    if not (exclude_doc_id in str(d.get("metadata", {}).get("id", ""))
                            or exclude_doc_id in str(d.get("metadata", {}).get("doc_id", "")))]

        if not docs:
            return 0.0

        # Score sur les 3 premiers docs restants
        top3 = docs[:3]
        return round(sum(d["score"] for d in top3) / len(top3), 3)
    except Exception:
        return 0.0


# Alias pour la rétrocompatibilité
def _get_rag_score(question: str) -> float:
    """Score RAG basique (sans exclusion). Utilisé avant l'indexation."""
    return _get_rag_score_honest(question, exclude_doc_id=None)


# ══════════════════════════════════════════════════════════════════════════════
# 6. GÉNÉRATION DE RÉPONSE EXPERTE
# ══════════════════════════════════════════════════════════════════════════════

HOODIEWEAR_CONTEXT = """
Base de connaissances HoodieWear :
• Livraison : 3-5 jours Tunisie | 5-10 jours Europe | 10-15 jours international
• Retours : 30 jours, article non porté, étiquettes intactes → support@hoodiewear.com
• Remboursement : 5-7 jours ouvrés après réception du retour
• Paiement : Visa, Mastercard, PayPal, virement, paiement à la livraison (+3 DT Tunisie)
• Tailles : XS à XXL | Guide des tailles sur le site | Oversized = taille au-dessus
• Entretien : 30°C max, à l'envers, sans sèche-linge, sans javel
• Annulation : gratuite dans les 24h après commande
• Défauts : photos par email → remplacement ou remboursement complet
• Double prélèvement : remboursement sous 5-7 jours sur justificatif
• Contact : support@hoodiewear.com | Chat lun-ven 9h-18h
• Boutique : 100% en ligne sur hoodiewear.com
"""

LANG_LABELS = {"fr": "français", "en": "English", "ar": "العربية"}


def _build_generation_prompt(question: str, lang: str,
                              bad_answer: str, attempt: int) -> str:
    """Construit le prompt LLM selon la tentative."""
    lang_label = LANG_LABELS.get(lang, "français")

    if attempt == 1:
        return f"""Tu es un expert du service client de HoodieWear, boutique streetwear.

{HOODIEWEAR_CONTEXT}

MISSION : Génère une réponse PARFAITE à cette question client.

Question : "{question}"
Réponse précédente insuffisante : "{bad_answer}"

CONTRAINTES STRICTES :
- Réponds UNIQUEMENT en {lang_label}
- Maximum 3 phrases claires et directes
- Inclus les délais/prix/procédures EXACTS si pertinent
- Utilise les mots-clés de la question dans ta réponse
- Si incertain, oriente vers support@hoodiewear.com
- Réponds UNIQUEMENT avec ce JSON (aucun texte avant/après) :
{{"reponse": "...", "tags": ["tag1", "tag2"], "mots_cles": ["mot1", "mot2", "mot3"]}}"""
    else:
        return f"""DEUXIÈME TENTATIVE — Sois encore plus précis et explicite.

{HOODIEWEAR_CONTEXT}

La première réponse générée n'a pas suffi à améliorer le score RAG.
Reformule en utilisant EXACTEMENT les termes de la question.

Question : "{question}"

CONTRAINTES RENFORCÉES :
- Réponds en {lang_label}
- Répète les mots-clés de la question dans ta réponse
- Donne des chiffres précis (délais, prix, pourcentages)
- Sois très explicite sur les étapes de la procédure
- Réponds UNIQUEMENT avec ce JSON :
{{"reponse": "...", "tags": ["tag1", "tag2"], "mots_cles": ["mot1", "mot2", "mot3", "mot4"]}}"""


def _generate_response(question: str, lang: str,
                        bad_answer: str, attempt: int) -> dict | None:
    """Appelle le LLM pour générer une réponse experte."""
    import re

    prompt = _build_generation_prompt(question, lang, bad_answer, attempt)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2 if attempt == 1 else 0.45,
            max_tokens=350
        )
        raw = response.choices[0].message.content.strip()

        # Nettoyage JSON
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```\s*",     "", raw)
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not match:
            return None

        parsed    = json.loads(match.group())
        reponse   = parsed.get("reponse", "").strip()
        tags      = parsed.get("tags", [detect_topic(question)])
        mots_cles = parsed.get("mots_cles", tags)

        if len(reponse) < MIN_RESPONSE_LEN:
            return None

        return {"reponse": reponse, "tags": tags, "mots_cles": mots_cles}

    except Exception as e:
        print(f"   ❌ Erreur génération (attempt {attempt}) : {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# 7. INDEXATION DANS CHROMADB
# ══════════════════════════════════════════════════════════════════════════════

def _index_new_knowledge(question: str, reponse: str,
                          tags: list, mots_cles: list,
                          lang: str) -> str:
    """
    Indexe immédiatement la nouvelle connaissance dans ChromaDB.
    Retourne le doc_id créé.
    """
    from src.indexer import get_collection

    collection = get_collection()

    doc_text = (
        f"Question: {question}\n"
        f"Réponse: {reponse}\n"
        f"Tags: {', '.join(tags)}\n"
        f"Mots-clés: {', '.join(mots_cles)}"
    )

    doc_id = f"learned_{hashlib.md5(question.encode()).hexdigest()[:12]}_{int(time.time())}"

    collection.add(
        documents=[doc_text],
        metadatas=[{
            "source":         LEARNED_FAQ_FILE,
            "tags":           ", ".join(tags),
            "keywords":       ", ".join(mots_cles),
            "auto_learned":   "true",
            "langue":         lang,
            "date_learned":   datetime.now().strftime("%Y-%m-%d %H:%M"),
            "doc_id":         doc_id,   # NOUVEAU : stocké dans metadata pour exclusion
        }],
        ids=[doc_id]
    )

    # Sauvegarde dans le fichier JSON pour l'historique (thread-safe)
    _save_learned_entry(question, reponse, tags, mots_cles, lang, doc_id)

    return doc_id


def _save_learned_entry(question: str, reponse: str,
                         tags: list, mots_cles: list,
                         lang: str, doc_id: str):
    """Persiste la nouvelle entrée dans le fichier JSON des apprentissages (thread-safe)."""
    os.makedirs("data/raw", exist_ok=True)

    new_entry = {
        "id":           doc_id,
        "question":     question,
        "reponse":      reponse,
        "tags":         tags,
        "mots_cles":    mots_cles,
        "langue":       lang,
        "source":       "auto_learned",
        "date":         datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    _safe_json_append(LEARNED_FAQ_FILE, new_entry, max_entries=1000)


# ══════════════════════════════════════════════════════════════════════════════
# 8. PIPELINE PRINCIPAL — AUTO_LEARN
# ══════════════════════════════════════════════════════════════════════════════

def auto_learn_from_feedback(question: str,
                              bad_answer: str,
                              lang: str = None) -> dict:
    """
    ⭐ FONCTION PRINCIPALE ⭐

    Déclenché automatiquement après un feedback 👎.
    Tente d'apprendre la réponse correcte et de l'indexer dans ChromaDB.

    Améliorations v3 :
    - Déduplication avant indexation (_is_already_indexed)
    - Score RAG honnête qui exclut le nouveau doc (_get_rag_score_honest)
    - Validation LLM des faits avant indexation (_validate_generated_response)
    - Écriture JSON thread-safe (_safe_json_append)

    Args:
        question   : question posée par le client
        bad_answer : réponse insuffisante donnée par le RAG
        lang       : langue détectée (fr/en/ar)

    Returns:
        dict : résultat complet de l'apprentissage
    """
    start_time = time.time()

    if lang is None:
        lang = detect_language(question)

    topic = detect_topic(question)

    print(f"\n🧠 [LEARNING] Démarrage apprentissage automatique")
    print(f"   Question : {question[:60]}...")
    print(f"   Topic    : {topic} | Langue : {lang}")

    result = {
        "question":       question,
        "topic":          topic,
        "lang":           lang,
        "score_before":   0.0,
        "score_after":    0.0,
        "improvement":    0.0,
        "status":         "failed",
        "attempts":       0,
        "doc_id":         None,
        "learned_answer": None,
        "duration_seconds": 0,
        "message":        ""
    }

    # ── NOUVEAU : Vérification déduplication ───────────────────────────────
    if _is_already_indexed(question, threshold=DEDUP_THRESHOLD):
        result["status"]  = "skipped"
        result["message"] = (
            f"Question déjà couverte dans la base (similarité >= {DEDUP_THRESHOLD}). "
            f"Apprentissage ignoré pour éviter les doublons."
        )
        print(f"   ⏭️  {result['message']}")
        result["duration_seconds"] = round(time.time() - start_time, 2)
        save_learning_event(result)
        return result

    # Score RAG AVANT apprentissage (honnête, sans doc appris)
    score_before = _get_rag_score(question)
    result["score_before"] = score_before
    result["score_after"]  = score_before
    print(f"   Score RAG avant : {score_before}")

    # ── Boucle de tentatives ──────────────────────────────────────────────────
    for attempt in range(1, MAX_ATTEMPTS + 1):
        result["attempts"] = attempt
        print(f"\n   [Tentative {attempt}/{MAX_ATTEMPTS}] Génération en cours...")

        generated = _generate_response(question, lang, bad_answer, attempt)

        if not generated:
            print(f"   ⚠️  Génération échouée (attempt {attempt})")
            continue

        reponse   = generated["reponse"]
        tags      = generated["tags"]
        mots_cles = generated["mots_cles"]

        print(f"   ✅ Réponse générée : {reponse[:80]}...")

        # ── NOUVEAU : Validation des faits LLM avant indexation ───────────
        validation = _validate_generated_response(question, reponse)
        if not validation.get("valid", True):
            print(f"   ⚠️  Réponse rejetée (faits incorrects) : {validation.get('issues')}")
            bad_answer = reponse   # La mauvaise réponse devient la nouvelle référence
            continue               # Tente la prochaine génération

        # Indexation immédiate
        doc_id = _index_new_knowledge(question, reponse, tags, mots_cles, lang)
        result["doc_id"]         = doc_id
        result["learned_answer"] = reponse

        # Petite pause pour que ChromaDB indexe
        time.sleep(0.5)

        # ── NOUVEAU : Score RAG HONNÊTE après apprentissage ───────────────
        # On exclut le document qu'on vient d'indexer pour éviter le faux positif
        score_after = _get_rag_score_honest(question, exclude_doc_id=doc_id)
        improvement = round(score_after - score_before, 3)

        print(f"   Score RAG après  : {score_after} (Δ {improvement:+.3f})")
        print(f"   [Note: doc '{doc_id}' exclu du calcul pour éviter faux positif]")

        result["score_after"]  = score_after
        result["improvement"]  = improvement

        # Succès si score amélioré OU dépasse le seuil
        if score_after >= SCORE_TARGET or improvement > 0.05:
            result["status"]  = "success"
            result["message"] = (
                f"Apprentissage réussi en {attempt} tentative(s). "
                f"Score : {score_before} → {score_after} (Δ{improvement:+.3f})"
            )
            print(f"   🎉 SUCCÈS ! {result['message']}")
            break
        else:
            print(f"   🔄 Score insuffisant ({score_after} < {SCORE_TARGET}), nouvelle tentative...")
            bad_answer = reponse

    # Si toutes les tentatives ont échoué
    if result["status"] == "failed":
        result["message"] = (
            f"Apprentissage partiel après {MAX_ATTEMPTS} tentative(s). "
            f"Score : {score_before} → {result['score_after']}"
        )
        print(f"   ⚠️  {result['message']}")

    result["duration_seconds"] = round(time.time() - start_time, 2)

    # Enregistrement dans le log (thread-safe)
    save_learning_event(result)

    return result


# ══════════════════════════════════════════════════════════════════════════════
# 9. APPRENTISSAGE EN BATCH
# ══════════════════════════════════════════════════════════════════════════════

def batch_learn_from_all_feedbacks() -> dict:
    """
    Analyse TOUS les feedbacks négatifs existants et tente d'apprendre
    pour chacun.
    """
    if not os.path.exists(FEEDBACK_FILE):
        return {"total": 0, "success": 0, "failed": 0, "details": []}

    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            feedbacks = json.loads(f.read().strip() or "[]")
    except Exception:
        return {"total": 0, "success": 0, "failed": 0, "details": []}

    negative = [f for f in feedbacks if f.get("rating") == "negative"]

    if not negative:
        return {"total": 0, "success": 0, "failed": 0, "details": []}

    print(f"\n🚀 Batch Learning : {len(negative)} feedbacks négatifs trouvés")

    results = []
    success = 0
    failed  = 0
    skipped = 0

    for i, fb in enumerate(negative, 1):
        question   = fb.get("question", "").strip()
        bad_answer = fb.get("answer", "")
        lang       = fb.get("langue", None)

        if not question:
            continue

        print(f"\n[{i}/{len(negative)}] Apprentissage pour : {question[:50]}...")
        result = auto_learn_from_feedback(question, bad_answer, lang)

        if result["status"] == "success":
            success += 1
        elif result["status"] == "skipped":
            skipped += 1
        else:
            failed += 1

        results.append(result)
        time.sleep(1)   # Pause pour respecter les limites de l'API

    total_attempted = success + failed
    summary = {
        "total":        len(results),
        "success":      success,
        "failed":       failed,
        "skipped":      skipped,
        "success_rate": round(success / total_attempted * 100, 1) if total_attempted > 0 else 0,
        "details":      results
    }

    print(f"\n✅ Batch Learning terminé : {success}/{total_attempted} réussis ({skipped} ignorés/doublons)")
    return summary


# ══════════════════════════════════════════════════════════════════════════════
# 10. APPRENTISSAGE DEPUIS LES GAPS TEMPS RÉEL
# ══════════════════════════════════════════════════════════════════════════════

def learn_from_realtime_gaps() -> dict:
    """
    Analyse les gaps détectés en temps réel (score RAG bas)
    et tente d'apprendre automatiquement pour chacun.
    """
    if not os.path.exists(PENDING_GAPS_FILE):
        return {"total": 0, "success": 0, "failed": 0}

    try:
        with open(PENDING_GAPS_FILE, "r", encoding="utf-8") as f:
            gaps = json.loads(f.read().strip() or "[]")
    except Exception:
        return {"total": 0, "success": 0, "failed": 0}

    untreated = [g for g in gaps if g.get("statut") == "non_traité"]

    if not untreated:
        return {"total": 0, "success": 0, "failed": 0}

    print(f"\n🔍 {len(untreated)} gaps temps réel à traiter...")

    success = 0
    failed  = 0

    for gap in untreated:
        question   = gap.get("question", "").strip()
        bad_answer = gap.get("answer", "")
        lang       = gap.get("langue", "fr")

        if not question:
            continue

        result = auto_learn_from_feedback(question, bad_answer, lang)

        if result["status"] in ("success", "skipped"):
            success += 1
            gap["statut"]          = "traité_auto"
            gap["date_resolution"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        else:
            failed += 1
            gap["statut"] = "traitement_partiel"

        time.sleep(0.8)

    # Sauvegarde les gaps mis à jour (thread-safe)
    _safe_json_write(PENDING_GAPS_FILE, gaps)

    return {"total": len(untreated), "success": success, "failed": failed}


# ══════════════════════════════════════════════════════════════════════════════
# 11. POINT D'ENTRÉE DIRECT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("🧠 Continuous Learning RAG — HoodieWear KMS v3")
    print("=" * 60)

    result = auto_learn_from_feedback(
        question="Comment suivre ma commande ?",
        bad_answer="Je n'ai pas trouvé d'information précise sur ce sujet.",
        lang="fr"
    )

    print(f"\n📊 Résultat : {result['message']}")
    print(f"   Score : {result['score_before']} → {result['score_after']}")
    print(f"   Durée : {result['duration_seconds']}s")