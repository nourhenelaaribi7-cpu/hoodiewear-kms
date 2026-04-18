# src/validator.py
"""
Module de validation automatique — Régression RAGAS quotidienne
===============================================================
Ce module implémente le job de validation nocturne qui :
  1. Re-exécute le jeu de 20 questions de test sur le système RAG actuel
  2. Compare les scores RAGAS à la session précédente
  3. Détecte les régressions (baisse > 5%) et génère des alertes
  4. Sauvegarde l'historique des scores pour le graphique d'évolution

Peut être exécuté :
  - Manuellement depuis la page 5_Evaluation.py
  - En tâche planifiée (cron, scheduler, etc.)

Usage direct :
    python -m src.validator
"""

import json
import os
from datetime import datetime
from src.rag_chain import answer_question

# ── Fichiers ────────────────────────────────────────────────────────────────────
SCORES_FILE         = "data/ragas_scores.json"
SCORES_HISTORY_FILE = "data/ragas_scores_history.json"
REGRESSION_FILE     = "data/ragas_regression_alerts.json"

# ── Seuil de régression ──────────────────────────────────────────────────────────
REGRESSION_THRESHOLD = 0.05   # baisse de plus de 5% → alerte

# ── Jeu de test étendu (20 questions) ───────────────────────────────────────────
# Minimum recommandé pour une évaluation statistiquement valide.
TEST_QUESTIONS = [
    # Livraison
    {
        "question":     "Quels sont les délais de livraison en Tunisie ?",
        "ground_truth": "Les délais de livraison sont de 3 à 5 jours ouvrés en Tunisie."
    },
    {
        "question":     "Combien de jours pour recevoir une commande depuis la France ?",
        "ground_truth": "La livraison en France prend entre 5 et 10 jours ouvrés."
    },
    {
        "question":     "Comment suivre ma commande HoodieWear ?",
        "ground_truth": "Vous recevez un email avec un lien de suivi après expédition."
    },
    {
        "question":     "Livrez-vous dans toute la Tunisie ?",
        "ground_truth": "Oui, nous livrons dans toutes les gouvernorats via nos partenaires logistiques."
    },
    # Retours & remboursements
    {
        "question":     "Comment retourner un article chez HoodieWear ?",
        "ground_truth": "Vous pouvez retourner un article sous 30 jours après réception, non porté avec étiquettes intactes."
    },
    {
        "question":     "Quel est le délai pour être remboursé après un retour ?",
        "ground_truth": "Le remboursement est effectué sous 5 à 7 jours ouvrés après réception du retour."
    },
    {
        "question":     "J'ai reçu un article défectueux, que faire ?",
        "ground_truth": "Contactez-nous avec des photos du défaut. Nous prenons en charge le retour et proposons un remplacement ou remboursement."
    },
    # Paiement
    {
        "question":     "Quels modes de paiement acceptez-vous ?",
        "ground_truth": "Nous acceptons les cartes bancaires Visa et Mastercard, PayPal, virement bancaire, et paiement à la livraison en Tunisie."
    },
    {
        "question":     "Est-ce que le paiement à la livraison est disponible ?",
        "ground_truth": "Oui, le paiement à la livraison est disponible en Tunisie avec un supplément de 3 DT."
    },
    {
        "question":     "Ma carte a été débitée deux fois, que faire ?",
        "ground_truth": "En cas de double prélèvement, envoyez une capture d'écran de vos relevés. Le remboursement est effectué sous 5 à 7 jours ouvrés."
    },
    # Tailles
    {
        "question":     "Comment choisir ma taille de hoodie ?",
        "ground_truth": "Consultez notre guide des tailles sur le site. Pour un style oversized, prenez une taille au-dessus."
    },
    {
        "question":     "Quelles tailles proposez-vous ?",
        "ground_truth": "Nous proposons les tailles XS, S, M, L, XL et XXL."
    },
    # Entretien
    {
        "question":     "À quelle température laver mon hoodie ?",
        "ground_truth": "Lavez votre hoodie à 30°C maximum, à l'envers, avec une lessive douce."
    },
    {
        "question":     "Puis-je mettre mon hoodie HoodieWear au sèche-linge ?",
        "ground_truth": "Non, évitez le sèche-linge. Séchez à l'air libre pour préserver les fibres et les impressions."
    },
    # Commande & compte
    {
        "question":     "Puis-je annuler ma commande ?",
        "ground_truth": "Vous pouvez annuler gratuitement dans les 24 heures suivant la commande en nous contactant par email."
    },
    {
        "question":     "Comment récupérer mon mot de passe ?",
        "ground_truth": "Cliquez sur 'Mot de passe oublié' sur la page de connexion et suivez le lien reçu par email."
    },
    # International
    {
        "question":     "Livrez-vous en Europe ?",
        "ground_truth": "Oui, nous livrons dans toute l'Europe en 5 à 10 jours ouvrés."
    },
    {
        "question":     "Quels sont les frais de livraison internationale ?",
        "ground_truth": "Les frais de livraison internationale sont calculés à la commande selon le pays et le poids."
    },
    # Contact & général
    {
        "question":     "Comment contacter le service client HoodieWear ?",
        "ground_truth": "Par email à support@hoodiewear.com (réponse sous 24h) ou via le chat en direct lun-ven 9h-18h."
    },
    {
        "question":     "HoodieWear a-t-il une boutique physique ?",
        "ground_truth": "Non, HoodieWear est une boutique 100% en ligne sur hoodiewear.com."
    },
]


def run_ragas_evaluation(test_questions: list = None) -> dict:
    """Évaluation RAGAS avec Groq au lieu d'OpenAI"""
    import os
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall
    )
    from langchain_groq import ChatGroq
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper

    # ── Configure Groq comme LLM pour RAGAS ───────────────────────────────────
    groq_llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.0
    )
    ragas_llm = LangchainLLMWrapper(groq_llm)

    # ── Embeddings locaux (pas d'OpenAI) ──────────────────────────────────────
    hf_embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )
    ragas_embeddings = LangchainEmbeddingsWrapper(hf_embeddings)

    # ── Configure chaque métrique ──────────────────────────────────────────────
    metrics = [faithfulness, answer_relevancy, context_precision, context_recall]
    for metric in metrics:
        metric.llm       = ragas_llm
        metric.embeddings = ragas_embeddings

    questions_list = []
    answers_list   = []
    contexts_list  = []
    ground_truths  = []
    failed         = []

    test_set = test_questions or TEST_QUESTIONS
    print(f"🔍 Évaluation RAGAS (Groq) sur {len(test_set)} questions...")

    for item in test_set:
        q = item["question"]
        try:
            result = answer_question(q)
            questions_list.append(q)
            answers_list.append(result["answer"])
            contexts_list.append([doc["content"] for doc in result["sources"]])
            ground_truths.append(item["ground_truth"])
            print(f"  ✅ {q[:50]}...")
        except Exception as e:
            print(f"  ❌ Erreur sur '{q[:40]}': {e}")
            failed.append(q)

    if not questions_list:
        raise ValueError("Aucune question n'a pu être évaluée.")

    dataset = Dataset.from_dict({
        "question":     questions_list,
        "answer":       answers_list,
        "contexts":     contexts_list,
        "ground_truth": ground_truths
    })

    result = evaluate(dataset, metrics=metrics)

    scores = {
        "faithfulness":      round(float(result["faithfulness"]), 3),
        "answer_relevancy":  round(float(result["answer_relevancy"]), 3),
        "context_precision": round(float(result["context_precision"]), 3),
        "context_recall":    round(float(result["context_recall"]), 3),
        "ragas_score":       round(float(sum([
            result["faithfulness"],
            result["answer_relevancy"],
            result["context_precision"],
            result["context_recall"]
        ]) / 4), 3),
        "nb_questions": len(questions_list),
        "nb_failed":    len(failed),
        "timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M"),
        "date":         datetime.now().strftime("%Y-%m-%d")
    }
    return scores


def save_scores(scores: dict):
    """Sauvegarde les scores courants dans ragas_scores.json."""
    os.makedirs("data", exist_ok=True)
    with open(SCORES_FILE, "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False, indent=2)


def append_to_history(scores: dict):
    """
    Ajoute les scores courants à l'historique pour le graphique d'évolution.
    Garde les 90 derniers points (≈ 3 mois de runs quotidiens).
    """
    history = []
    if os.path.exists(SCORES_HISTORY_FILE):
        try:
            with open(SCORES_HISTORY_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                history = json.loads(content) if content else []
        except Exception:
            history = []

    history.append(scores)
    history = history[-90:]

    with open(SCORES_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def detect_regressions(current: dict) -> list:
    """
    Compare les scores courants avec la session précédente.
    Retourne une liste d'alertes si une métrique a baissé de plus de
    REGRESSION_THRESHOLD (5%).

    Returns:
        list[dict] : liste d'alertes (vide si aucune régression).
    """
    history = []
    if os.path.exists(SCORES_HISTORY_FILE):
        try:
            with open(SCORES_HISTORY_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                history = json.loads(content) if content else []
        except Exception:
            return []

    if len(history) < 2:
        return []     # Pas assez d'historique pour comparer

    previous = history[-2]   # La session avant la courante

    metrics = ["faithfulness", "answer_relevancy", "context_precision",
               "context_recall", "ragas_score"]
    alerts  = []

    for metric in metrics:
        prev_val = previous.get(metric, 0)
        curr_val = current.get(metric, 0)
        if prev_val > 0:
            drop = prev_val - curr_val
            if drop > REGRESSION_THRESHOLD:
                alerts.append({
                    "metric":     metric,
                    "previous":   prev_val,
                    "current":    curr_val,
                    "drop":       round(drop, 3),
                    "drop_pct":   round(drop / prev_val * 100, 1),
                    "date":       current.get("timestamp", ""),
                    "severity":   "critique" if drop > 0.10 else "avertissement"
                })

    return alerts


def save_regression_alerts(alerts: list):
    """Persiste les alertes de régression pour l'interface Admin."""
    existing = []
    if os.path.exists(REGRESSION_FILE):
        try:
            with open(REGRESSION_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                existing = json.loads(content) if content else []
        except Exception:
            existing = []

    existing.extend(alerts)
    existing = existing[-50:]     # garde les 50 dernières alertes

    os.makedirs("data", exist_ok=True)
    with open(REGRESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


def load_regression_alerts() -> list:
    """Charge les alertes de régression pour affichage dans l'interface."""
    if not os.path.exists(REGRESSION_FILE):
        return []
    try:
        with open(REGRESSION_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else []
    except Exception:
        return []


def load_scores_history() -> list:
    """Charge l'historique des scores pour le graphique d'évolution."""
    if not os.path.exists(SCORES_HISTORY_FILE):
        return []
    try:
        with open(SCORES_HISTORY_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else []
    except Exception:
        return []


def run_full_validation_pipeline() -> dict:
    """
    Pipeline complet :
      1. Évaluation RAGAS (20 questions)
      2. Sauvegarde des scores courants
      3. Ajout à l'historique
      4. Détection des régressions
      5. Sauvegarde des alertes si nécessaire

    Returns:
        dict : {scores, alerts, has_regression}
    """
    print("=" * 60)
    print("🔬 Pipeline de validation automatique — HoodieWear KMS")
    print("=" * 60)

    scores = run_ragas_evaluation()
    save_scores(scores)
    append_to_history(scores)

    alerts = detect_regressions(scores)
    if alerts:
        save_regression_alerts(alerts)
        print(f"\n⚠️  {len(alerts)} régression(s) détectée(s) !")
        for a in alerts:
            print(f"   {a['metric']}: {a['previous']} → {a['current']} "
                  f"(↓ {a['drop_pct']}%) [{a['severity']}]")
    else:
        print("\n✅ Aucune régression détectée.")

    print(f"\n📊 Scores courants :")
    print(f"   Faithfulness      : {scores['faithfulness']}")
    print(f"   Answer Relevancy  : {scores['answer_relevancy']}")
    print(f"   Context Precision : {scores['context_precision']}")
    print(f"   Context Recall    : {scores['context_recall']}")
    print(f"   RAGAS Score moyen : {scores['ragas_score']}")
    print(f"   Questions testées : {scores['nb_questions']}")

    return {
        "scores":          scores,
        "alerts":          alerts,
        "has_regression":  len(alerts) > 0
    }


if __name__ == "__main__":
    run_full_validation_pipeline()
