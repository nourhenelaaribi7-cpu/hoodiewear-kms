# src/knowledge_gap.py
"""
Module d'Intelligence KM — Knowledge Gap Detector + Auto-amélioration
====================================================================
Améliorations v2 :
  1. Boucle de correction FERMÉE  : validate_correction() teste le score
     RAG avant ET après indexation et stocke le delta.
  2. Correction Rate              : % de lacunes réellement corrigées,
     exposé dans get_km_health_score().
  3. Regénération automatique    : si la correction échoue (score après
     toujours bas), une 2e tentative est lancée avec un prompt renforcé.
  4. Module prédictif            : get_predictive_gaps() analyse la
     tendance des 7 derniers jours et signale les sujets émergents avant
     qu'ils ne génèrent des feedbacks négatifs.
  5. Formule fraicheur corrigée  : basée sur le Correction Rate réel,
     non sur le volume de documents générés.
  6. Déduplication sémantique   : utilise semantic_deduplicate_gaps()
     du retriever au lieu du groupement par mots-clés.

Basé sur Nonaka & Takeuchi (1995), modèle SECI.
"""

import os
import json
import re
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
SCORE_LACUNE_SEUIL  = 0.40   # score RAG en-dessous duquel c'est une lacune
SCORE_CORRECTED     = 0.55   # score RAG cible après correction
MIN_FREQ_LACUNE     = 1      # dès la 1ère occurrence, on signale
MAX_REGEN_ATTEMPTS  = 2      # nombre maximum de re-générations si correction échoue


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
    os.makedirs("data", exist_ok=True)
    with open(GAP_FILE, "w", encoding="utf-8") as f:
        json.dump(gaps, f, ensure_ascii=False, indent=2)


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
    os.makedirs("data", exist_ok=True)
    with open(CORRECTION_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════════════════════
# 2. DÉTECTION DES LACUNES
# ══════════════════════════════════════════════════════════════════════════════

def detect_gaps_from_feedbacks() -> list:
    """
    Analyse les feedbacks négatifs pour identifier les lacunes.
    Retourne une liste de gaps enrichis triés par fréquence.
    """
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
        # Sentiment dominant
        sentiment_counts = Counter(data["sentiments"])
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
    """
    Analyse l'historique + le fichier de tracking temps réel
    pour détecter les questions avec score RAG bas.
    """
    gaps = []
    seen = set()

    # Source 1 : fichier de tracking temps réel (rag_chain.py → _track_potential_gap)
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

    # Source 2 : historique des conversations (messages avec avg_score stocké)
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
    """
    Fusionne toutes les sources de lacunes détectées et applique
    la déduplication sémantique.
    """
    from src.retriever import semantic_deduplicate_gaps

    gaps_fb    = detect_gaps_from_feedbacks()
    gaps_score = detect_gaps_from_low_scores()

    # Fusion avec déduplication basique par clé normalisée
    existing_questions = {_normalize_question(g["question"]) for g in gaps_fb}
    for g in gaps_score:
        if _normalize_question(g["question"]) not in existing_questions:
            gaps_fb.append(g)
            existing_questions.add(_normalize_question(g["question"]))

    # Déduplication sémantique (remplace le groupement naïf par mots-clés)
    try:
        all_gaps = semantic_deduplicate_gaps(gaps_fb, threshold=0.85)
    except Exception:
        # Fallback si ChromaDB n'est pas disponible
        all_gaps = gaps_fb

    return all_gaps


# ══════════════════════════════════════════════════════════════════════════════
# 3. MODULE PRÉDICTIF — Anticiper les lacunes futures
# ══════════════════════════════════════════════════════════════════════════════

def get_predictive_gaps(window_days: int = 7) -> list:
    """
    Analyse les tendances des derniers `window_days` jours.
    Identifie les sujets dont la fréquence augmente mais dont le score
    RAG moyen reste bas → lacune émergente avant d'avoir des feedbacks négatifs.

    Returns:
        list[dict] : lacunes prédites avec score de tendance et sujet.
    """
    history   = load_history()
    feedbacks = load_feedbacks()
    cutoff    = datetime.now() - timedelta(days=window_days)

    # Collecte les questions récentes
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
                    "score":    None     # sera rempli ci-dessous
                })

    if not recent_questions:
        return []

    # Catégorisation par sujet
    categories = {
        "livraison":     ["livraison", "livrer", "délai", "expédition", "colis", "shipping", "delivery"],
        "retour":        ["retour", "retourner", "échange", "rembours", "return", "refund"],
        "taille":        ["taille", "tailles", "size", "xl", "xxl", "mesure", "guide"],
        "paiement":      ["paiement", "payer", "carte", "paypal", "virement", "payment"],
        "commande":      ["commande", "commander", "annuler", "suivre", "tracking", "order"],
        "compte":        ["compte", "connexion", "mot de passe", "email", "login", "password"],
        "produit":       ["hoodie", "qualité", "couleur", "défaut", "entretien", "laver"],
    }

    topic_questions: dict[str, list] = {cat: [] for cat in categories}
    for item in recent_questions:
        q_lower = item["question"].lower()
        for cat, keywords in categories.items():
            if any(kw in q_lower for kw in keywords):
                topic_questions[cat].append(item["question"])
                break

    # Calcul du score RAG moyen par sujet (sur un échantillon)
    from src.retriever import get_avg_score_for_query

    predictive = []
    for cat, questions in topic_questions.items():
        if len(questions) < 2:
            continue
        sample = questions[:3]   # On limite les appels ChromaDB
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
                "id":           f"pred_{cat}_{datetime.now().strftime('%Y%m%d')}",
                "sujet":        cat,
                "frequence_7j": len(questions),
                "score_rag_moyen": avg_score,
                "type":         "predictif",
                "statut":       "non_traité",
                "question":     f"[PRÉDICTIF] Sujets émergents sur : {cat} ({len(questions)} questions récentes, score moyen {avg_score})",
                "langue":       "fr",
                "questions_exemple": questions[:3]
            })

    predictive.sort(key=lambda x: x["frequence_7j"], reverse=True)
    return predictive


# ══════════════════════════════════════════════════════════════════════════════
# 4. GÉNÉRATION DE RÉPONSES (SECI : Combinaison)
# ══════════════════════════════════════════════════════════════════════════════

def _build_generation_prompt(question: str, langue: str,
                              reponse_actuelle: str,
                              attempt: int = 1) -> str:
    """
    Construit le prompt de génération.
    attempt=2 → prompt renforcé si la 1ère correction a échoué.
    """
    lang_map = {"fr": "français", "en": "English", "ar": "العربية"}
    lang_label = lang_map.get(langue, "français")

    base_context = """Contexte HoodieWear :
- Livraison : 3-5 jours Tunisie, 5-10 jours Europe, 10-15 jours international
- Retours : 30 jours, articles non portés, étiquettes intactes
- Paiement : Visa, Mastercard, PayPal, virement, paiement à la livraison (+3 DT en Tunisie)
- Tailles : XS à XXL, guide des tailles disponible sur le site
- Contact : support@hoodiewear.com | Chat lun-ven 9h-18h
- Boutique : 100% en ligne, hoodiewear.com"""

    if attempt == 1:
        instruction = f"""MISSION : Génère une réponse professionnelle et précise pour cette question client.

Question : "{question}"
Réponse précédente insuffisante : "{reponse_actuelle}"

{base_context}

CONTRAINTES :
- Réponds en {lang_label} uniquement
- Maximum 3 phrases claires
- Inclus les délais/prix/procédures spécifiques si pertinent
- Ne dis jamais "je ne sais pas" — oriente toujours vers support@hoodiewear.com si incertain
- Format JSON uniquement :
{{"reponse": "...", "tags": ["tag1", "tag2"], "mots_cles": ["mot1", "mot2"]}}"""
    else:
        instruction = f"""MISSION (2e tentative — sois encore plus précis) :
La 1ère réponse générée n'a pas amélioré le score RAG. Reformule la réponse
en utilisant des termes plus proches des questions clients habituelles.

Question : "{question}"

{base_context}

CONTRAINTES RENFORCÉES :
- Réponds en {lang_label}
- Utilise exactement les mots-clés de la question dans ta réponse
- Sois très explicite sur les délais, procédures et contacts
- Format JSON uniquement :
{{"reponse": "...", "tags": ["tag1", "tag2"], "mots_cles": ["mot1", "mot2", "mot3"]}}"""

    return instruction


def generate_answer_for_gap(gap: dict, attempt: int = 1) -> dict | None:
    """
    Utilise le LLM pour générer une réponse experte à une lacune détectée.

    Args:
        gap     : dict de la lacune
        attempt : 1 = génération normale, 2 = prompt renforcé (re-génération)

    Returns:
        dict {question, reponse, tags, mots_cles, langue, gap_id} ou None.
    """
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

        # Nettoyage du JSON
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```\s*", "", raw)
        raw = raw.strip()

        # Extraction du premier objet JSON
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not match:
            return None

        parsed = json.loads(match.group())
        reponse    = parsed.get("reponse", "").strip()
        tags       = parsed.get("tags", _extract_tags(question))
        mots_cles  = parsed.get("mots_cles", tags)

        if not reponse or len(reponse) < 20:
            return None

        return {
            "id":             f"auto_{abs(hash(question)) % 100000:05d}",
            "gap_id":         gap.get("id", ""),
            "question":       question,
            "reponse":        reponse,
            "tags":           tags,
            "mots_cles":      mots_cles,
            "langue":         langue,
            "source":         "auto_generated",
            "statut":         "en_attente",
            "date_creation":  datetime.now().strftime("%Y-%m-%d %H:%M"),
            "score_rag_avant": gap.get("score_rag_avant"),
            "attempt":        attempt
        }

    except Exception as e:
        print(f"❌ Erreur génération (attempt {attempt}) : {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# 5. BOUCLE DE CORRECTION FERMÉE — NOUVEAU
# ══════════════════════════════════════════════════════════════════════════════

def validate_correction(question: str, score_before: float) -> dict:
    """
    Teste si l'indexation d'un nouveau document a réellement amélioré
    le score RAG pour la question donnée.

    Returns:
        dict avec keys:
          score_before  : score RAG avant correction
          score_after   : score RAG après correction (re-testé maintenant)
          corrected     : bool — True si le score a dépassé SCORE_CORRECTED
          delta         : score_after - score_before
    """
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
    """Enregistre le résultat de chaque tentative de correction."""
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
    save_correction_log(log[-200:])   # garde les 200 derniers logs


def get_correction_rate() -> dict:
    """
    Calcule le Correction Rate : % de lacunes réellement corrigées
    après indexation (score RAG amélioré au-delà du seuil).

    Returns:
        dict : correction_rate, nb_corrected, nb_attempted, avg_delta
    """
    log = load_correction_log()

    # Un gap peut avoir plusieurs tentatives — on prend la dernière
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

    all_entries    = list(latest_per_gap.values())
    nb_corrected   = sum(1 for e in all_entries if e.get("corrected"))
    nb_attempted   = len(all_entries)
    avg_delta      = round(
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
    """
    Valide une entrée générée, l'indexe dans ChromaDB, puis valide
    automatiquement que la correction a bien amélioré le score RAG.

    Si la correction échoue, une 2e tentative de génération est proposée.

    Returns:
        dict avec keys: success, validation, needs_regen
    """
    try:
        # 1. Sauvegarde dans le fichier FAQ auto-généré
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
        with open(GAP_FAQ_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

        # 2. Indexation directe dans ChromaDB
        _index_single_entry(entry)

        # 3. Validation post-correction (boucle FERMÉE)
        score_before = entry.get("score_rag_avant") or 0.0
        validation   = validate_correction(entry["question"], score_before)
        attempt      = entry.get("attempt", 1)

        # 4. Log de la correction
        _log_correction(
            gap_id=entry.get("gap_id", entry["id"]),
            question=entry["question"],
            validation=validation,
            attempt=attempt
        )

        # 5. Mise à jour du gap avec les scores avant/après
        _update_gap_scores(
            gap_id=entry.get("gap_id", ""),
            score_before=score_before,
            score_after=validation["score_after"],
            corrected=validation["corrected"]
        )

        # 6. Si correction réussie → marquer le gap comme traité
        if validation["corrected"]:
            _mark_gap_as_resolved(entry.get("gap_id", ""))

        print(f"✅ Indexé : {entry['question'][:60]}...")
        print(f"   Score avant: {validation['score_before']} → après: {validation['score_after']} "
              f"| Corrigé: {validation['corrected']} | Delta: {validation['delta']:+.3f}")

        return {
            "success":      True,
            "validation":   validation,
            "needs_regen":  not validation["corrected"] and attempt < MAX_REGEN_ATTEMPTS
        }

    except Exception as e:
        print(f"❌ Erreur indexation : {e}")
        return {"success": False, "validation": None, "needs_regen": False}


def _index_single_entry(entry: dict):
    """Indexe un seul document dans ChromaDB sans réindexer tout."""
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
            "attempt":        str(entry.get("attempt", 1))
        }],
        ids=[doc_id]
    )


def _mark_gap_as_resolved(gap_id: str):
    """Marque un gap comme résolu dans knowledge_gaps.json."""
    gaps = load_gaps()
    for g in gaps:
        if g.get("id") == gap_id:
            g["statut"]          = "traité"
            g["date_resolution"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_gaps(gaps)


def _update_gap_scores(gap_id: str, score_before: float,
                        score_after: float, corrected: bool):
    """Met à jour les scores avant/après dans knowledge_gaps.json."""
    gaps = load_gaps()
    for g in gaps:
        if g.get("id") == gap_id:
            g["score_rag_avant"] = score_before
            g["score_rag_apres"] = score_after
            g["correction_ok"]   = corrected
            g["delta_score"]     = round(score_after - score_before, 3)
    save_gaps(gaps)


# ══════════════════════════════════════════════════════════════════════════════
# 7. KM HEALTH SCORE — Formule corrigée
# ══════════════════════════════════════════════════════════════════════════════

def get_km_health_score() -> dict:
    """
    Calcule le score de santé de la base de connaissances.

    Dimensions (pondération) :
      1. Satisfaction client   (35%) : taux de feedbacks positifs
      2. Couverture sujets     (30%) : inverse du nb de lacunes ouvertes
      3. Fraîcheur / qualité   (15%) : Correction Rate réel (remplace le volume)
      4. Réactivité KM         (20%) : % de gaps traités

    Chaque dimension est normalisée sur 100.
    """
    feedbacks       = load_feedbacks()
    gaps            = get_all_gaps()
    correction_info = get_correction_rate()

    total_fb  = len(feedbacks)
    positifs  = len([f for f in feedbacks if f.get("rating") == "positive"])

    # Dim 1 : Satisfaction (0-100)
    satisfaction = (positifs / total_fb * 100) if total_fb > 0 else 50

    # Dim 2 : Couverture (0-100)
    nb_gaps    = len(gaps)
    nb_traites = len([g for g in gaps if g.get("statut") == "traité"])
    nb_ouverts = nb_gaps - nb_traites
    couverture = max(0.0, 100.0 - nb_ouverts * 12) if nb_ouverts > 0 else 100.0

    # Dim 3 : Fraîcheur = Correction Rate réel (0-100)
    # Avant : basé sur len(auto_docs) * 20 → circulaire et trompeur
    # Maintenant : % de lacunes réellement corrigées avec delta score positif
    fraicheur = correction_info["correction_rate"]
    if correction_info["nb_attempted"] == 0:
        fraicheur = 50.0    # valeur neutre si aucune correction tentée

    # Dim 4 : Réactivité (0-100)
    reactivite = (nb_traites / nb_gaps * 100) if nb_gaps > 0 else 100.0

    # Score global pondéré
    score_global = round(
        satisfaction * 0.35 +
        couverture   * 0.30 +
        fraicheur    * 0.15 +
        reactivite   * 0.20
    , 1)

    # Compte les docs auto-générés pour affichage
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
    """Analyse la distribution des sujets dans les questions posées."""
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
        "livraison":     ["livraison", "livrer", "délai", "expédition", "colis", "shipping", "delivery", "شحن", "توصيل"],
        "retour":        ["retour", "retourner", "échange", "rembours", "return", "refund", "إرجاع", "استرداد"],
        "taille":        ["taille", "tailles", "size", "xl", "xxl", "mesure", "guide", "مقاس", "قياس"],
        "paiement":      ["paiement", "payer", "carte", "paypal", "virement", "payment", "دفع", "بطاقة"],
        "commande":      ["commande", "commander", "annuler", "suivre", "tracking", "order", "طلب", "تتبع"],
        "compte":        ["compte", "connexion", "mot de passe", "email", "login", "password", "حساب", "كلمة"],
        "produit":       ["hoodie", "qualité", "couleur", "défaut", "entretien", "laver", "منتج", "جودة"],
        "autre":         []
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
    """Normalise une question pour le regroupement (fallback sans embeddings)."""
    q = q.lower().strip()
    q = re.sub(r'[^\w\s]', '', q)
    q = re.sub(r'\s+', ' ', q)
    words = [w for w in q.split() if len(w) > 2][:8]   # 8 mots au lieu de 6
    return " ".join(words)


def _detect_lang_simple(text: str) -> str:
    """Détection de langue rapide (sans dépendance externe)."""
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
    """Extrait automatiquement des tags depuis une question."""
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