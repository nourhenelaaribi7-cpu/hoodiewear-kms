# src/knowledge_gap.py
"""
Module d'Intelligence KM — Knowledge Gap Detector + Auto-amélioration
====================================================================
CORRECTIONS v3 :
  - Toutes les écritures JSON utilisent _safe_json_write() (thread-safe)
  - Imports nettoyés
"""

import os
import json
import re
import threading
from datetime import datetime, timedelta
from collections import Counter
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── Fichiers ────────────────────────────────────────────────────────────────────
FEEDBACK_FILE        = "data/feedback.json"
HISTORY_FILE         = "data/historique.json"
GAP_FILE             = "data/knowledge_gaps.json"
FAQ_FILE             = "data/raw/faq_hoodiewear.json"
GAP_FAQ_FILE         = "data/raw/faq_auto_generated.json"
REALTIME_GAPS_FILE   = "data/potential_gaps_realtime.json"
CORRECTION_LOG_FILE  = "data/correction_log.json"

# ── Seuils ──────────────────────────────────────────────────────────────────────
SCORE_LACUNE_SEUIL  = 0.40
SCORE_CORRECTED     = 0.55
MIN_FREQ_LACUNE     = 1
MAX_REGEN_ATTEMPTS  = 2

# ── Lock thread-safe ────────────────────────────────────────────────────────────
_json_lock = threading.Lock()


# ══════════════════════════════════════════════════════════════════════════════
# UTILITAIRE — Écriture JSON thread-safe
# ══════════════════════════════════════════════════════════════════════════════

def _safe_json_write(filepath: str, data):
    """Écriture thread-safe via fichier temporaire (opération atomique)."""
    with _json_lock:
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
        tmp = filepath + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, filepath)
        except Exception as e:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise e


# ══════════════════════════════════════════════════════════════════════════════
# 1. CHARGEMENT DES DONNÉES
# ══════════════════════════════════════════════════════════════════════════════

def load_feedbacks() -> list:
    if not os.path.exists(FEEDBACK_FILE):
        return []
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else []
    except Exception:
        return []


def load_history() -> list:
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else []
    except Exception:
        return []


def load_gaps() -> list:
    if not os.path.exists(GAP_FILE):
        return []
    try:
        with open(GAP_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else []
    except Exception:
        return []


def save_gaps(gaps: list):
    _safe_json_write(GAP_FILE, gaps)


def load_correction_log() -> list:
    if not os.path.exists(CORRECTION_LOG_FILE):
        return []
    try:
        with open(CORRECTION_LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else []
    except Exception:
        return []


def save_correction_log(log: list):
    _safe_json_write(CORRECTION_LOG_FILE, log)


# ══════════════════════════════════════════════════════════════════════════════
# 2. DÉTECTION DES LACUNES
# ══════════════════════════════════════════════════════════════════════════════

def detect_gaps_from_feedbacks() -> list:
    feedbacks = load_feedbacks()
    negative  = [f for f in feedbacks if f.get("rating") == "negative"]

    if not negative:
        return []

    gap_map = {}
    for fb in negative:
        q   = fb.get("question", "").strip()
        key = _normalize_question(q)
        if key not in gap_map:
            gap_map[key] = {
                "question_originale": q,
                "occurrences":        0,
                "dates":              [],
                "reponses_donnees":   [],
                "langue":             _detect_lang_simple(q),
                "sentiments":         []
            }
        gap_map[key]["occurrences"]       += 1
        gap_map[key]["dates"].append(fb.get("date", ""))
        gap_map[key]["reponses_donnees"].append(fb.get("answer", "")[:150])
        gap_map[key]["sentiments"].append(fb.get("sentiment", "neutre"))

    gaps = []
    for key, data in gap_map.items():
        sentiment_counts   = Counter(data["sentiments"])
        dominant_sentiment = sentiment_counts.most_common(1)[0][0]

        gaps.append({
            "id":                  f"gap_{abs(hash(key)) % 100000:05d}",
            "question":            data["question_originale"],
            "occurrences":         data["occurrences"],
            "derniere_occurrence": data["dates"][-1] if data["dates"] else "",
            "langue":              data["langue"],
            "reponse_actuelle":    data["reponses_donnees"][-1] if data["reponses_donnees"] else "",
            "statut":              "non_traité",
            "type":                "feedback_negatif",
            "sentiment_dominant":  dominant_sentiment,
            "score_rag_avant":     None,
            "score_rag_apres":     None,
            "correction_ok":       None
        })

    gaps.sort(key=lambda x: x["occurrences"], reverse=True)
    return gaps


def detect_gaps_from_low_scores() -> list:
    gaps = []
    seen = set()

    if os.path.exists(REALTIME_GAPS_FILE):
        try:
            with open(REALTIME_GAPS_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                realtime = json.loads(content) if content else []
            for item in realtime:
                q   = item.get("question", "").strip()
                key = _normalize_question(q)
                if key not in seen:
                    seen.add(key)
                    gaps.append({
                        "id":        f"gap_rt_{abs(hash(key)) % 100000:05d}",
                        "question":  q,
                        "score_rag": item.get("score_rag", 0),
                        "date":      item.get("date", ""),
                        "langue":    item.get("langue", "fr"),
                        "statut":    "non_traité",
                        "type":      "score_bas",
                        "score_rag_avant": item.get("score_rag", 0),
                        "score_rag_apres": None,
                        "correction_ok":   None
                    })
        except Exception:
            pass

    history = load_history()
    for conv in history:
        for idx, msg in enumerate(conv.get("messages", [])):
            if msg.get("role") == "assistant":
                score = msg.get("avg_score", 1.0)
                if idx > 0 and conv["messages"][idx - 1]["role"] == "user":
                    q   = conv["messages"][idx - 1]["content"]
                    key = _normalize_question(q)
                    if score < SCORE_LACUNE_SEUIL and score > 0 and key not in seen:
                        seen.add(key)
                        gaps.append({
                            "id":              f"gap_hist_{abs(hash(key)) % 100000:05d}",
                            "question":        q,
                            "score_rag":       round(score, 3),
                            "date":            conv.get("date", ""),
                            "langue":          _detect_lang_simple(q),
                            "statut":          "non_traité",
                            "type":            "score_bas",
                            "score_rag_avant": round(score, 3),
                            "score_rag_apres": None,
                            "correction_ok":   None
                        })

    return gaps


def get_all_gaps() -> list:
    from src.retriever import semantic_deduplicate_gaps

    gaps_fb    = detect_gaps_from_feedbacks()
    gaps_score = detect_gaps_from_low_scores()

    existing_questions = {_normalize_question(g["question"]) for g in gaps_fb}
    for g in gaps_score:
        if _normalize_question(g["question"]) not in existing_questions:
            gaps_fb.append(g)
            existing_questions.add(_normalize_question(g["question"]))

    try:
        all_gaps = semantic_deduplicate_gaps(gaps_fb, threshold=0.85)
    except Exception:
        all_gaps = gaps_fb

    return all_gaps


# ══════════════════════════════════════════════════════════════════════════════
# 3. MODULE PRÉDICTIF
# ══════════════════════════════════════════════════════════════════════════════

def get_predictive_gaps(window_days: int = 7) -> list:
    history   = load_history()
    cutoff    = datetime.now() - timedelta(days=window_days)

    recent_questions = []
    for conv in history:
        try:
            conv_date = datetime.strptime(conv.get("date", ""), "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        if conv_date < cutoff:
            continue
        for msg in conv.get("messages", []):
            if msg.get("role") == "user":
                recent_questions.append({
                    "question": msg["content"],
                    "date":     conv["date"],
                })

    if not recent_questions:
        return []

    categories = {
        "livraison":  ["livraison", "livrer", "délai", "expédition", "colis", "shipping", "delivery"],
        "retour":     ["retour", "retourner", "échange", "rembours", "return", "refund"],
        "taille":     ["taille", "tailles", "size", "xl", "xxl", "mesure", "guide"],
        "paiement":   ["paiement", "payer", "carte", "paypal", "virement", "payment"],
        "commande":   ["commande", "commander", "annuler", "suivre", "tracking", "order"],
        "compte":     ["compte", "connexion", "mot de passe", "email", "login", "password"],
        "produit":    ["hoodie", "qualité", "couleur", "défaut", "entretien", "laver"],
    }

    topic_questions: dict[str, list] = {cat: [] for cat in categories}
    for item in recent_questions:
        q_lower = item["question"].lower()
        for cat, keywords in categories.items():
            if any(kw in q_lower for kw in keywords):
                topic_questions[cat].append(item["question"])
                break

    from src.retriever import get_avg_score_for_query

    predictive = []
    for cat, questions in topic_questions.items():
        if len(questions) < 2:
            continue
        sample = questions[:3]
        scores = []
        for q in sample:
            try:
                s = get_avg_score_for_query(q, n_results=3)
                scores.append(s)
            except Exception:
                pass

        avg_score = round(sum(scores) / len(scores), 3) if scores else 0.5

        if avg_score < SCORE_LACUNE_SEUIL and len(questions) >= 2:
            predictive.append({
                "id":              f"pred_{cat}_{datetime.now().strftime('%Y%m%d')}",
                "sujet":           cat,
                "frequence_7j":    len(questions),
                "score_rag_moyen": avg_score,
                "type":            "predictif",
                "statut":          "non_traité",
                "question":        f"[PRÉDICTIF] Sujets émergents : {cat} ({len(questions)} questions, score {avg_score})",
                "langue":          "fr",
                "questions_exemple": questions[:3]
            })

    predictive.sort(key=lambda x: x["frequence_7j"], reverse=True)
    return predictive


# ══════════════════════════════════════════════════════════════════════════════
# 4. GÉNÉRATION DE RÉPONSES
# ══════════════════════════════════════════════════════════════════════════════

def _build_generation_prompt(question: str, langue: str,
                              reponse_actuelle: str,
                              attempt: int = 1) -> str:
    lang_map   = {"fr": "français", "en": "English", "ar": "العربية"}
    lang_label = lang_map.get(langue, "français")

    base_context = """Contexte HoodieWear :
- Livraison : 3-5 jours Tunisie, 5-10 jours Europe, 10-15 jours international
- Retours : 30 jours, articles non portés, étiquettes intactes
- Paiement : Visa, Mastercard, PayPal, virement, paiement à la livraison (+3 DT en Tunisie)
- Tailles : XS à XXL, guide des tailles disponible sur le site
- Contact : support@hoodiewear.com | Chat lun-ven 9h-18h
- Boutique : 100% en ligne, hoodiewear.com"""

    if attempt == 1:
        return f"""MISSION : Génère une réponse professionnelle pour cette question client HoodieWear.

Question : "{question}"
Réponse précédente insuffisante : "{reponse_actuelle}"

{base_context}

CONTRAINTES :
- Réponds en {lang_label} uniquement
- Maximum 3 phrases claires
- Inclus les délais/prix/procédures spécifiques si pertinent
- Si incertain → oriente vers support@hoodiewear.com
- Format JSON uniquement :
{{"reponse": "...", "tags": ["tag1", "tag2"], "mots_cles": ["mot1", "mot2"]}}"""
    else:
        return f"""MISSION (2e tentative) :
La 1ère réponse n'a pas amélioré le score RAG. Reformule en utilisant des termes
plus proches des questions clients habituelles.

Question : "{question}"

{base_context}

CONTRAINTES RENFORCÉES :
- Réponds en {lang_label}
- Utilise exactement les mots-clés de la question
- Donne des délais, procédures et contacts précis
- Format JSON uniquement :
{{"reponse": "...", "tags": ["tag1", "tag2"], "mots_cles": ["mot1", "mot2", "mot3"]}}"""


def generate_answer_for_gap(gap: dict, attempt: int = 1) -> dict | None:
    question         = gap.get("question", "")
    langue           = gap.get("langue", "fr")
    reponse_actuelle = gap.get("reponse_actuelle", "Aucune réponse fournie.")

    prompt = _build_generation_prompt(question, langue, reponse_actuelle, attempt)

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2 if attempt == 1 else 0.4,
            max_tokens=400
        )

        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```\s*", "", raw)

        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not match:
            return None

        parsed    = json.loads(match.group())
        reponse   = parsed.get("reponse", "").strip()
        tags      = parsed.get("tags", _extract_tags(question))
        mots_cles = parsed.get("mots_cles", tags)

        if not reponse or len(reponse) < 20:
            return None

        return {
            "id":              f"auto_{abs(hash(question)) % 100000:05d}",
            "gap_id":          gap.get("id", ""),
            "question":        question,
            "reponse":         reponse,
            "tags":            tags,
            "mots_cles":       mots_cles,
            "langue":          langue,
            "source":          "auto_generated",
            "statut":          "en_attente",
            "date_creation":   datetime.now().strftime("%Y-%m-%d %H:%M"),
            "score_rag_avant": gap.get("score_rag_avant"),
            "attempt":         attempt
        }

    except Exception as e:
        print(f"❌ Erreur génération (attempt {attempt}) : {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# 5. BOUCLE DE CORRECTION FERMÉE
# ══════════════════════════════════════════════════════════════════════════════

def validate_correction(question: str, score_before: float) -> dict:
    from src.retriever import get_avg_score_for_query

    score_after = get_avg_score_for_query(question, n_results=3)
    corrected   = score_after >= SCORE_CORRECTED and score_after > score_before

    return {
        "score_before": round(score_before, 3),
        "score_after":  round(score_after, 3),
        "corrected":    corrected,
        "delta":        round(score_after - score_before, 3)
    }


def _log_correction(gap_id: str, question: str, validation: dict, attempt: int):
    log = load_correction_log()
    log.append({
        "gap_id":       gap_id,
        "question":     question[:100],
        "date":         datetime.now().strftime("%Y-%m-%d %H:%M"),
        "attempt":      attempt,
        "score_before": validation["score_before"],
        "score_after":  validation["score_after"],
        "delta":        validation["delta"],
        "corrected":    validation["corrected"]
    })
    save_correction_log(log[-200:])


def get_correction_rate() -> dict:
    log = load_correction_log()

    latest_per_gap: dict[str, dict] = {}
    for entry in log:
        gid = entry.get("gap_id", entry.get("question", ""))
        latest_per_gap[gid] = entry

    if not latest_per_gap:
        return {
            "correction_rate": 0.0,
            "nb_corrected":    0,
            "nb_attempted":    0,
            "avg_delta":       0.0
        }

    all_entries  = list(latest_per_gap.values())
    nb_corrected = sum(1 for e in all_entries if e.get("corrected"))
    nb_attempted = len(all_entries)
    avg_delta    = round(
        sum(e.get("delta", 0) for e in all_entries) / nb_attempted, 3
    )

    return {
        "correction_rate": round(nb_corrected / nb_attempted * 100, 1),
        "nb_corrected":    nb_corrected,
        "nb_attempted":    nb_attempted,
        "avg_delta":       avg_delta
    }


# ══════════════════════════════════════════════════════════════════════════════
# 6. VALIDATION & INDEXATION
# ══════════════════════════════════════════════════════════════════════════════

def approve_and_index_entry(entry: dict) -> dict:
    try:
        existing = []
        if os.path.exists(GAP_FAQ_FILE):
            try:
                with open(GAP_FAQ_FILE, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    existing = json.loads(content) if content else []
            except Exception:
                existing = []

        entry["statut"]          = "validé"
        entry["date_validation"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        existing.append(entry)

        os.makedirs("data/raw", exist_ok=True)
        _safe_json_write(GAP_FAQ_FILE, existing)

        _index_single_entry(entry)

        score_before = entry.get("score_rag_avant") or 0.0
        validation   = validate_correction(entry["question"], score_before)
        attempt      = entry.get("attempt", 1)

        _log_correction(
            gap_id=entry.get("gap_id", entry["id"]),
            question=entry["question"],
            validation=validation,
            attempt=attempt
        )

        _update_gap_scores(
            gap_id=entry.get("gap_id", ""),
            score_before=score_before,
            score_after=validation["score_after"],
            corrected=validation["corrected"]
        )

        if validation["corrected"]:
            _mark_gap_as_resolved(entry.get("gap_id", ""))

        print(f"✅ Indexé : {entry['question'][:60]}...")
        print(f"   Score avant: {validation['score_before']} → après: {validation['score_after']} "
              f"| Corrigé: {validation['corrected']}")

        return {
            "success":      True,
            "validation":   validation,
            "needs_regen":  not validation["corrected"] and attempt < MAX_REGEN_ATTEMPTS
        }

    except Exception as e:
        print(f"❌ Erreur indexation : {e}")
        return {"success": False, "validation": None, "needs_regen": False}


def _index_single_entry(entry: dict):
    from src.indexer import get_collection

    collection = get_collection()
    doc_text   = f"Question: {entry['question']}\nRéponse: {entry['reponse']}"
    doc_id     = f"auto_{entry['id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    collection.add(
        documents=[doc_text],
        metadatas=[{
            "source":         GAP_FAQ_FILE,
            "tags":           str(entry.get("tags", [])),
            "keywords":       str(entry.get("mots_cles", [])),
            "auto_generated": "true",
            "date":           entry.get("date_creation", ""),
            "attempt":        str(entry.get("attempt", 1)),
            "doc_id":         doc_id,    # NOUVEAU : pour exclusion dans le scoring
        }],
        ids=[doc_id]
    )


def _mark_gap_as_resolved(gap_id: str):
    gaps = load_gaps()
    for g in gaps:
        if g.get("id") == gap_id:
            g["statut"]          = "traité"
            g["date_resolution"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_gaps(gaps)


def _update_gap_scores(gap_id: str, score_before: float,
                        score_after: float, corrected: bool):
    gaps = load_gaps()
    for g in gaps:
        if g.get("id") == gap_id:
            g["score_rag_avant"] = score_before
            g["score_rag_apres"] = score_after
            g["correction_ok"]   = corrected
            g["delta_score"]     = round(score_after - score_before, 3)
    save_gaps(gaps)


# ══════════════════════════════════════════════════════════════════════════════
# 7. KM HEALTH SCORE
# ══════════════════════════════════════════════════════════════════════════════

def get_km_health_score() -> dict:
    feedbacks       = load_feedbacks()
    gaps            = get_all_gaps()
    correction_info = get_correction_rate()

    total_fb  = len(feedbacks)
    positifs  = len([f for f in feedbacks if f.get("rating") == "positive"])

    satisfaction = (positifs / total_fb * 100) if total_fb > 0 else 50

    nb_gaps    = len(gaps)
    nb_traites = len([g for g in gaps if g.get("statut") == "traité"])
    nb_ouverts = nb_gaps - nb_traites
    couverture = max(0.0, 100.0 - nb_ouverts * 12) if nb_ouverts > 0 else 100.0

    fraicheur = correction_info["correction_rate"]
    if correction_info["nb_attempted"] == 0:
        fraicheur = 50.0

    reactivite = (nb_traites / nb_gaps * 100) if nb_gaps > 0 else 100.0

    score_global = round(
        satisfaction * 0.35 +
        couverture   * 0.30 +
        fraicheur    * 0.15 +
        reactivite   * 0.20
    , 1)

    auto_docs = []
    if os.path.exists(GAP_FAQ_FILE):
        try:
            with open(GAP_FAQ_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                auto_docs = json.loads(content) if content else []
        except Exception:
            pass

    return {
        "score_global":     score_global,
        "satisfaction":     round(satisfaction, 1),
        "couverture":       round(couverture, 1),
        "fraicheur":        round(fraicheur, 1),
        "reactivite":       round(reactivite, 1),
        "nb_gaps_ouverts":  nb_ouverts,
        "nb_gaps_traites":  nb_traites,
        "nb_auto_docs":     len(auto_docs),
        "total_feedbacks":  total_fb,
        "correction_rate":  correction_info["correction_rate"],
        "avg_delta_score":  correction_info["avg_delta"],
        "nb_corrected":     correction_info["nb_corrected"],
        "nb_attempted":     correction_info["nb_attempted"]
    }


# ══════════════════════════════════════════════════════════════════════════════
# 8. DISTRIBUTION DES SUJETS
# ══════════════════════════════════════════════════════════════════════════════

def get_topic_distribution() -> dict:
    history   = load_history()
    feedbacks = load_feedbacks()

    all_questions = []
    for conv in history:
        for msg in conv.get("messages", []):
            if msg.get("role") == "user":
                all_questions.append(msg["content"])
    for fb in feedbacks:
        all_questions.append(fb.get("question", ""))

    categories = {
        "livraison": ["livraison", "livrer", "délai", "expédition", "colis", "shipping", "delivery", "شحن", "توصيل"],
        "retour":    ["retour", "retourner", "échange", "rembours", "return", "refund", "إرجاع", "استرداد"],
        "taille":    ["taille", "tailles", "size", "xl", "xxl", "mesure", "guide", "مقاس", "قياس"],
        "paiement":  ["paiement", "payer", "carte", "paypal", "virement", "payment", "دفع", "بطاقة"],
        "commande":  ["commande", "commander", "annuler", "suivre", "tracking", "order", "طلب", "تتبع"],
        "compte":    ["compte", "connexion", "mot de passe", "email", "login", "password", "حساب", "كلمة"],
        "produit":   ["hoodie", "qualité", "couleur", "défaut", "entretien", "laver", "منتج", "جودة"],
        "autre":     []
    }

    counts = {cat: 0 for cat in categories}
    for q in all_questions:
        if not q:
            continue
        q_lower = q.lower()
        matched = False
        for cat, keywords in categories.items():
            if cat == "autre":
                continue
            if any(kw in q_lower for kw in keywords):
                counts[cat] += 1
                matched = True
                break
        if not matched:
            counts["autre"] += 1

    return counts


# ══════════════════════════════════════════════════════════════════════════════
# 9. UTILITAIRES INTERNES
# ══════════════════════════════════════════════════════════════════════════════

def _normalize_question(q: str) -> str:
    q = q.lower().strip()
    q = re.sub(r'[^\w\s]', '', q)
    q = re.sub(r'\s+', ' ', q)
    words = [w for w in q.split() if len(w) > 2][:8]
    return " ".join(words)


def _detect_lang_simple(text: str) -> str:
    arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    if arabic_chars > 2:
        return "ar"
    english_words = {"what", "how", "when", "where", "why", "can", "is", "the",
                     "my", "order", "delivery", "return", "size", "help", "i",
                     "do", "does", "please", "want", "need"}
    words = set(text.lower().split())
    if len(words & english_words) >= 2:
        return "en"
    return "fr"


def _extract_tags(question: str) -> list:
    tag_map = {
        "livraison":     ["livraison", "livrer", "délai", "expédition", "delivery", "shipping", "توصيل"],
        "retour":        ["retour", "rembours", "échange", "return", "refund", "إرجاع"],
        "taille":        ["taille", "size", "mesure", "xl", "xxl", "قياس"],
        "paiement":      ["paiement", "carte", "paypal", "payment", "دفع"],
        "commande":      ["commande", "commander", "annuler", "order", "طلب"],
        "compte":        ["compte", "mot de passe", "connexion", "login", "حساب"],
        "qualite":       ["défaut", "qualité", "hoodie", "entretien"],
        "international": ["international", "france", "europe", "دولي"]
    }

    q_lower = question.lower()
    tags = [tag for tag, keywords in tag_map.items()
            if any(kw in q_lower for kw in keywords)]

    return tags if tags else ["general"]