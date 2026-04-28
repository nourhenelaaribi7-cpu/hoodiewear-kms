"""
src/judge_llm.py
================
Évaluateur LLM-as-a-Judge — HoodieWear KMS v3.0
Adapté depuis Portalyze JudgeLLM.py

Métriques RAGAS adaptées au service client :
  - Faithfulness    : réponse ancrée dans les docs RAG (pas d'hallucination)
  - Answer Relevancy: répond à la question posée
  - Context Precision: les docs récupérés sont-ils pertinents ?
  - Completeness    : la réponse est-elle complète et utile ?

Usage :
    from src.judge_llm import HoodieJudge
    judge = HoodieJudge()
    result = judge.evaluate(question, answer, context, sources)
"""

import os
import re
import json
import time
from typing import Optional
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Modèle léger pour économiser les tokens
MODEL_JUDGE = "llama-3.1-8b-instant"

JUDGE_LOG_FILE = "data/judge_log.json"

# ── Faits HoodieWear (même liste que learning_pipeline.py) ─────────────────────
HOODIEWEAR_FACTS = """
Faits officiels HoodieWear (vérifiés) :
- Livraison Tunisie : 3-5 jours (jamais < 2, jamais > 7)
- Livraison Europe : 5-10 jours
- Livraison internationale : 10-15 jours
- Retours : 30 jours maximum
- Paiement à la livraison : supplément 3 DT
- Email support : support@hoodiewear.com
- Tailles : XS, S, M, L, XL, XXL
- Remboursement après retour : 5-7 jours ouvrés
- Annulation gratuite : dans les 24h
- Entretien : 30°C max, à l'envers, sans sèche-linge
"""


class HoodieJudge:
    """
    Juge LLM pour évaluer la qualité des réponses RAG de HoodieWear.
    Adapté depuis Portalyze LLMJudge.evaluate()
    """

    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    # ──────────────────────────────────────────────────────────────────────────
    # MÉTRIQUES INDIVIDUELLES
    # ──────────────────────────────────────────────────────────────────────────

    def _score_faithfulness(self, question: str,
                             answer: str, context: str) -> dict:
        """
        Faithfulness : la réponse est-elle ancrée dans le contexte ?
        Ne contient-elle pas d'hallucinations ?
        """
        prompt = f"""Évalue si la réponse suivante est fidèle au contexte fourni.
Une réponse infidèle invente des informations non présentes dans le contexte.

CONTEXTE :
{context[:1200]}

RÉPONSE :
{answer}

FAITS OFFICIELS HOODIEWEAR :
{HOODIEWEAR_FACTS}

Score 1.0 = parfaitement fidèle (tout vient du contexte ou des faits)
Score 0.0 = hallucinations graves (délais, prix ou procédures inventés)

Réponds UNIQUEMENT avec ce JSON :
{{"score": 0.0, "reason": "..."}}"""

        return self._call_judge(prompt, metric="faithfulness")

    def _score_relevancy(self, question: str, answer: str) -> dict:
        """
        Answer Relevancy : la réponse répond-elle à la question ?
        """
        prompt = f"""Évalue si la réponse répond directement à la question.

QUESTION : {question}
RÉPONSE  : {answer}

Score 1.0 = répond parfaitement à la question
Score 0.5 = répond partiellement
Score 0.0 = hors sujet ou évasive

Réponds UNIQUEMENT avec ce JSON :
{{"score": 0.0, "reason": "..."}}"""

        return self._call_judge(prompt, metric="relevancy")

    def _score_context_precision(self, question: str,
                                  sources: list) -> dict:
        """
        Context Precision : les documents récupérés sont-ils pertinents ?
        Adapté depuis Portalyze structure_check_prompt()
        """
        if not sources:
            return {"score": 0.0, "reason": "Aucune source récupérée"}

        sources_text = "\n".join([
            f"[Doc {i+1}] score={s.get('score',0):.2f} : {s.get('content','')[:200]}"
            for i, s in enumerate(sources[:5])
        ])

        prompt = f"""Évalue si les documents récupérés sont pertinents pour répondre à la question.

QUESTION : {question}

DOCUMENTS RÉCUPÉRÉS :
{sources_text}

Score 1.0 = tous les docs sont très pertinents
Score 0.5 = certains docs sont hors sujet
Score 0.0 = aucun doc n'est pertinent

Réponds UNIQUEMENT avec ce JSON :
{{"score": 0.0, "reason": "..."}}"""

        return self._call_judge(prompt, metric="context_precision")

    def _score_completeness(self, question: str, answer: str) -> dict:
        """
        Completeness : la réponse est-elle suffisamment complète et utile ?
        """
        prompt = f"""Évalue si la réponse est suffisamment complète pour un client HoodieWear.

QUESTION : {question}
RÉPONSE  : {answer}

Critères :
- Donne-t-elle une information actionnable ?
- Y a-t-il des étapes ou chiffres concrets si nécessaire ?
- Le client saurait-il quoi faire après cette réponse ?

Score 1.0 = réponse complète et actionnable
Score 0.5 = réponse partielle
Score 0.0 = trop vague ou inutile

Réponds UNIQUEMENT avec ce JSON :
{{"score": 0.0, "reason": "..."}}"""

        return self._call_judge(prompt, metric="completeness")

    # ──────────────────────────────────────────────────────────────────────────
    # APPEL LLM JUGE (modèle léger)
    # ──────────────────────────────────────────────────────────────────────────

    def _call_judge(self, prompt: str, metric: str) -> dict:
        """
        Appelle le LLM juge (MODEL_LIGHT) et parse le JSON de résultat.
        Adapté depuis Portalyze LLMJudge._ask_model()
        """
        try:
            response = self.client.chat.completions.create(
                model=MODEL_JUDGE,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=120,
            )
            raw   = response.choices[0].message.content.strip()
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
                return {
                    "score":  round(float(parsed.get("score", 0.5)), 3),
                    "reason": parsed.get("reason", ""),
                }
        except Exception as e:
            print(f"⚠️  Judge {metric} échoué: {e}")

        return {"score": 0.5, "reason": "Évaluation indisponible"}

    # ──────────────────────────────────────────────────────────────────────────
    # ÉVALUATION COMPLÈTE
    # ──────────────────────────────────────────────────────────────────────────

    def evaluate(self, question: str, answer: str,
                 context: str = "", sources: list = None,
                 save_log: bool = True) -> dict:
        """
        Évaluation complète d'une paire (question, réponse).
        Adapté depuis Portalyze LLMJudge.evaluate()

        Args:
            question : question posée par le client
            answer   : réponse générée par le RAG
            context  : contexte formaté fourni au LLM
            sources  : liste des docs récupérés (avec scores)
            save_log : persiste le résultat dans judge_log.json

        Returns:
            dict avec toutes les métriques + verdict global
        """
        start = time.time()

        # Évaluation des 4 métriques (en parallèle possible mais on garde simple)
        faithfulness       = self._score_faithfulness(question, answer, context)
        relevancy          = self._score_relevancy(question, answer)
        context_precision  = self._score_context_precision(question, sources or [])
        completeness       = self._score_completeness(question, answer)

        # Score global pondéré
        # Faithfulness et relevancy sont les plus importants
        weights = {
            "faithfulness":      0.35,
            "relevancy":         0.30,
            "context_precision": 0.20,
            "completeness":      0.15,
        }
        global_score = round(
            faithfulness["score"]      * weights["faithfulness"]
            + relevancy["score"]       * weights["relevancy"]
            + context_precision["score"] * weights["context_precision"]
            + completeness["score"]    * weights["completeness"],
            3
        )

        # Verdict
        verdict = "pass" if global_score >= 0.55 else "fail"

        # Issues agrégées
        issues = []
        for name, result in [
            ("faithfulness",      faithfulness),
            ("relevancy",         relevancy),
            ("context_precision", context_precision),
            ("completeness",      completeness),
        ]:
            if result["score"] < 0.5 and result.get("reason"):
                issues.append(f"{name}: {result['reason']}")

        duration = round(time.time() - start, 2)

        result = {
            "verdict":          verdict,
            "global_score":     global_score,
            "faithfulness":     faithfulness["score"],
            "relevancy":        relevancy["score"],
            "context_precision": context_precision["score"],
            "completeness":     completeness["score"],
            "issues":           issues,
            "question":         question[:100],
            "duration_seconds": duration,
            "timestamp":        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        if save_log:
            self._save_log(result)

        print(
            f"⚖️  Judge: score={global_score} | "
            f"F={faithfulness['score']} R={relevancy['score']} "
            f"P={context_precision['score']} C={completeness['score']} "
            f"→ {verdict.upper()}"
        )

        return result

    # ──────────────────────────────────────────────────────────────────────────
    # BATCH EVALUATION (pour RAGAS complet)
    # ──────────────────────────────────────────────────────────────────────────

    def evaluate_batch(self, test_cases: list,
                       delay: float = 0.5) -> dict:
        """
        Évalue une liste de cas de test.
        Adapté depuis Portalyze LLMJudge.run()

        Args:
            test_cases : liste de dict {question, answer, context, sources}
            delay      : délai entre appels (rate limiting Groq)

        Returns:
            dict avec stats globales + détails par cas
        """
        results = []
        for i, case in enumerate(test_cases, 1):
            print(f"\n[{i}/{len(test_cases)}] Évaluation : {case['question'][:50]}...")
            result = self.evaluate(
                question=case["question"],
                answer=case.get("answer", ""),
                context=case.get("context", ""),
                sources=case.get("sources", []),
                save_log=False,  # On sauvegarde tout à la fin
            )
            results.append({**case, **result})
            time.sleep(delay)

        if not results:
            return {"total": 0, "passed": 0, "failed": 0, "avg_score": 0.0}

        passed     = [r for r in results if r["verdict"] == "pass"]
        avg_score  = round(sum(r["global_score"] for r in results) / len(results), 3)
        avg_faith  = round(sum(r["faithfulness"] for r in results) / len(results), 3)
        avg_relev  = round(sum(r["relevancy"] for r in results) / len(results), 3)
        avg_prec   = round(sum(r["context_precision"] for r in results) / len(results), 3)
        avg_compl  = round(sum(r["completeness"] for r in results) / len(results), 3)

        summary = {
            "total":            len(results),
            "passed":           len(passed),
            "failed":           len(results) - len(passed),
            "pass_rate":        round(len(passed) / len(results) * 100, 1),
            "avg_global_score": avg_score,
            "avg_faithfulness": avg_faith,
            "avg_relevancy":    avg_relev,
            "avg_context_precision": avg_prec,
            "avg_completeness": avg_compl,
            "details":          results,
            "timestamp":        datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

        # Sauvegarde du batch complet
        os.makedirs("data", exist_ok=True)
        batch_file = f"data/judge_batch_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(batch_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print(f"\n✅ Batch terminé : {len(passed)}/{len(results)} passés | Score moyen: {avg_score}")
        return summary

    # ──────────────────────────────────────────────────────────────────────────
    # LOG
    # ──────────────────────────────────────────────────────────────────────────

    def _save_log(self, result: dict):
        """Persiste chaque évaluation dans judge_log.json"""
        os.makedirs("data", exist_ok=True)
        existing = []
        if os.path.exists(JUDGE_LOG_FILE):
            try:
                with open(JUDGE_LOG_FILE, "r", encoding="utf-8") as f:
                    existing = json.loads(f.read().strip() or "[]")
            except Exception:
                existing = []

        existing.append(result)
        existing = existing[-500:]  # Garde les 500 derniers

        with open(JUDGE_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

    def get_stats(self) -> dict:
        """Statistiques globales depuis le log"""
        if not os.path.exists(JUDGE_LOG_FILE):
            return {"total": 0, "pass_rate": 0, "avg_score": 0}

        try:
            with open(JUDGE_LOG_FILE, "r", encoding="utf-8") as f:
                log = json.loads(f.read().strip() or "[]")
        except Exception:
            return {"total": 0, "pass_rate": 0, "avg_score": 0}

        if not log:
            return {"total": 0, "pass_rate": 0, "avg_score": 0}

        passed    = [e for e in log if e.get("verdict") == "pass"]
        avg_score = round(sum(e.get("global_score", 0) for e in log) / len(log), 3)

        return {
            "total":      len(log),
            "passed":     len(passed),
            "failed":     len(log) - len(passed),
            "pass_rate":  round(len(passed) / len(log) * 100, 1),
            "avg_score":  avg_score,
            "last_eval":  log[-1].get("timestamp", ""),
        }


# ── Singleton ──────────────────────────────────────────────────────────────────
_judge = None

def get_judge() -> HoodieJudge:
    global _judge
    if _judge is None:
        _judge = HoodieJudge()
    return _judge


# ── Test rapide ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    judge = HoodieJudge()
    result = judge.evaluate(
        question="Quels sont les délais de livraison en Tunisie ?",
        answer="La livraison en Tunisie prend entre 3 et 5 jours ouvrés.",
        context="Livraison Tunisie : 3-5 jours | Europe : 5-10 jours",
        sources=[{"score": 0.85, "content": "Livraison Tunisie : 3-5 jours"}]
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))