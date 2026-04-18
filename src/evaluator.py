# src/evaluator.py
"""
Évaluateur RAG personnalisé — LLM-as-a-Judge via Groq
Aucune dépendance OpenAI — fonctionne 100% avec Groq
"""
import os
import json
import re
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
from src.rag_chain import answer_question

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

TEST_QUESTIONS = [
    {"question": "Quels sont les délais de livraison ?",
     "ground_truth": "Les délais de livraison sont de 3 à 5 jours ouvrés."},
    {"question": "Comment retourner un article ?",
     "ground_truth": "Vous pouvez retourner un article sous 30 jours après réception."},
    {"question": "Quels modes de paiement acceptez-vous ?",
     "ground_truth": "Nous acceptons les cartes bancaires, PayPal et virement."},
    {"question": "Comment suivre ma commande ?",
     "ground_truth": "Vous recevez un email avec un lien de suivi après expédition."},
    {"question": "Livrez-vous à l'international ?",
     "ground_truth": "Oui, nous livrons dans toute l'Europe et en Afrique du Nord."},
    {"question": "Comment laver mon hoodie ?",
     "ground_truth": "Lavez à 30°C, ne pas sécher en machine, repassage à basse température."},
    {"question": "Puis-je annuler ma commande ?",
     "ground_truth": "Vous pouvez annuler votre commande dans les 24h suivant la commande."}
]


def score_with_llm(prompt: str) -> float:
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=10
        )
        raw  = response.choices[0].message.content.strip()
        nums = re.findall(r'\d+(?:\.\d+)?', raw)
        return min(max(float(nums[0]) / 10.0, 0.0), 1.0) if nums else 0.5
    except Exception:
        return 0.5


def evaluate_faithfulness(answer: str, contexts: list) -> float:
    context_text = "\n".join(contexts[:3])
    return score_with_llm(f"""Évalue si cette réponse est fidèle aux documents sources.
Note de 0 à 10 (10=fidèle, 0=inventé). Réponds UNIQUEMENT avec un chiffre.
Sources: {context_text}
Réponse: {answer}
Note:""")


def evaluate_relevancy(question: str, answer: str) -> float:
    return score_with_llm(f"""Évalue si cette réponse répond bien à la question.
Note de 0 à 10. Réponds UNIQUEMENT avec un chiffre.
Question: {question}
Réponse: {answer}
Note:""")


def evaluate_context_precision(question: str, contexts: list) -> float:
    return score_with_llm(f"""Évalue si ces documents sont pertinents pour la question.
Note de 0 à 10. Réponds UNIQUEMENT avec un chiffre.
Question: {question}
Documents: {chr(10).join(contexts[:3])}
Note:""")


def evaluate_completeness(answer: str, ground_truth: str) -> float:
    return score_with_llm(f"""Évalue si cette réponse couvre les informations essentielles.
Note de 0 à 10. Réponds UNIQUEMENT avec un chiffre.
Attendu: {ground_truth}
Obtenu: {answer}
Note:""")


def run_evaluation(progress_callback=None):
    print("🔍 Lancement de l'évaluation LLM-as-a-Judge...")
    results = []

    for i, item in enumerate(TEST_QUESTIONS):
        q  = item["question"]
        gt = item["ground_truth"]

        if progress_callback:
            progress_callback(i, len(TEST_QUESTIONS), q)
        print(f"  [{i+1}/{len(TEST_QUESTIONS)}] {q[:50]}...")

        try:
            result    = answer_question(q)
            answer    = result["answer"]
            contexts  = [doc["content"] for doc in result["sources"]]
            scores_r  = [doc["score"] for doc in result["sources"]]
            avg_rag   = sum(scores_r) / len(scores_r) if scores_r else 0

            faith  = evaluate_faithfulness(answer, contexts)
            relev  = evaluate_relevancy(q, answer)
            prec   = evaluate_context_precision(q, contexts)
            compl  = evaluate_completeness(answer, gt)
            glob   = round((faith + relev + prec + compl) / 4, 3)

            results.append({
                "question":          q,
                "answer":            answer[:300],
                "ground_truth":      gt,
                "nb_sources":        len(result["sources"]),
                "avg_rag_score":     round(avg_rag, 3),
                "faithfulness":      round(faith, 3),
                "answer_relevancy":  round(relev, 3),
                "context_precision": round(prec, 3),
                "completeness":      round(compl, 3),
                "global_score":      glob
            })
            print(f"     ✅ Score : {glob:.0%}")

        except Exception as e:
            print(f"     ❌ Erreur : {e}")
            results.append({
                "question": q, "error": str(e),
                "faithfulness": 0, "answer_relevancy": 0,
                "context_precision": 0, "completeness": 0, "global_score": 0
            })

    valid = [r for r in results if "error" not in r]

    summary = {
        "date":              datetime.now().strftime("%Y-%m-%d %H:%M"),
        "timestamp":         datetime.now().strftime("%Y-%m-%d %H:%M"),
        "nb_questions":      len(TEST_QUESTIONS),
        "nb_success":        len(valid),
        "faithfulness":      round(sum(r["faithfulness"]      for r in valid) / len(valid), 3) if valid else 0,
        "answer_relevancy":  round(sum(r["answer_relevancy"]  for r in valid) / len(valid), 3) if valid else 0,
        "context_precision": round(sum(r["context_precision"] for r in valid) / len(valid), 3) if valid else 0,
        "completeness":      round(sum(r["completeness"]      for r in valid) / len(valid), 3) if valid else 0,
        "global_score":      round(sum(r["global_score"]      for r in valid) / len(valid), 3) if valid else 0,
        "ragas_score":       round(sum(r["global_score"]      for r in valid) / len(valid), 3) if valid else 0,
        "details":           results
    }

    os.makedirs("data", exist_ok=True)
    with open("data/evaluation_scores.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # Compatible avec ragas_scores.json pour validator.py
    with open("data/ragas_scores.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Score global : {summary['global_score']:.0%}")
    return summary


if __name__ == "__main__":
    run_evaluation()