"""
src/rag_pipeline.py
===================
Pipeline RAG orchestré avec LangGraph — HoodieWear KMS v3.0
Adapté depuis Portalyze pipeline.py

Flux :
  sanitize → detect_lang → sentiment → cache? → retrieve
  → judge_context → generate → judge_answer → learn? → respond

Avantages vs rag_chain.py :
  - Chaque étape est un nœud indépendant → testable unitairement
  - État partagé typé (RAGState) → pas de kwargs éparpillés
  - Retry automatique si le juge rejette la réponse
  - Branchements conditionnels clairs (cache hit, escalation, token limit)
"""

import os
import time
import hashlib
from typing import Optional, Iterator
from typing_extensions import TypedDict, Annotated
from datetime import datetime

from langgraph.graph import StateGraph, END
from groq import Groq
from dotenv import load_dotenv

from src.retriever import retrieve_relevant_docs, format_context
from src.sentiment import analyze_sentiment, get_escalation_needed
from src.rag_chain import (
    sanitize_input, detect_language, get_language_instruction,
    _get_cache_key, _get_from_cache, _save_to_cache,
    _is_near_limit, _track_potential_gap,
    suggest_followup_questions,
    SYSTEM_PROMPT, DEFAULT_RESPONSES, ESCALATION_MESSAGE,
    MODEL_MAIN, MODEL_LIGHT, RAG_LACUNE_SEUIL,
    _save_token_usage, get_token_usage,
)

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── Seuils ─────────────────────────────────────────────────────────────────────
JUDGE_MIN_SCORE      = 0.55   # Score minimum pour accepter une réponse
MAX_RETRIES          = 2      # Tentatives max avant fallback
MIN_CONTEXT_SCORE    = 0.30   # Score RAG minimum pour continuer


# ══════════════════════════════════════════════════════════════════════════════
# STATE — Tout le contexte d'une requête
# ══════════════════════════════════════════════════════════════════════════════

class RAGState(TypedDict):
    # Entrée
    question:          str
    chat_history:      list

    # Pré-traitement
    clean_question:    str
    language:          str
    sentiment:         dict

    # Cache
    from_cache:        bool
    cache_key:         str

    # Retrieval
    retrieved_docs:    list
    context:           str
    avg_score:         float

    # Génération
    answer:            str
    attempt:           int

    # Évaluation
    judge_result:      dict

    # Post-traitement
    suggestions:       list
    escalation:        bool

    # Contrôle de flux
    status:            str   # "ok" | "cache_hit" | "escalation" | "token_limit" | "no_docs" | "done"
    error:             Optional[str]


# ══════════════════════════════════════════════════════════════════════════════
# NŒUDS DU PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def node_preprocess(state: RAGState) -> RAGState:
    """
    Nœud 1 — Sanitize + detect language + analyze sentiment
    Adapté depuis Portalyze : verif_node (validation entrée)
    """
    question = sanitize_input(state["question"])
    lang     = detect_language(question)
    sentiment = analyze_sentiment(question)

    return {
        **state,
        "clean_question": question,
        "language":       lang,
        "sentiment":      sentiment,
        "cache_key":      _get_cache_key(question, lang),
        "status":         "ok",
    }


def node_check_escalation(state: RAGState) -> RAGState:
    """
    Nœud 2 — Vérifie si escalade vers agent humain nécessaire
    """
    s = state["sentiment"]
    if get_escalation_needed(s["sentiment"], s["scores"].get("frustré", 0)):
        lang     = state["language"]
        fallback = ESCALATION_MESSAGE.get(lang, ESCALATION_MESSAGE["french"])
        return {
            **state,
            "answer":     fallback,
            "escalation": True,
            "status":     "escalation",
            "suggestions": [],
        }
    return {**state, "escalation": False}


def node_check_cache(state: RAGState) -> RAGState:
    """
    Nœud 3 — Cherche dans le cache MD5
    """
    cached = _get_from_cache(state["cache_key"])
    if cached:
        print(f"✅ Cache hit ! (économie tokens)")
        lang = state["language"]
        sugg = suggest_followup_questions(
            state["clean_question"], cached["answer"], lang
        )
        return {
            **state,
            "answer":      cached["answer"],
            "from_cache":  True,
            "suggestions": sugg,
            "status":      "cache_hit",
        }
    return {**state, "from_cache": False}


def node_check_token_limit(state: RAGState) -> RAGState:
    """
    Nœud 4 — Vérifie la limite quotidienne Groq (95k tokens)
    """
    if _is_near_limit():
        lang     = state["language"]
        fallback = DEFAULT_RESPONSES.get(lang, DEFAULT_RESPONSES["french"])
        fallback += "\n\n⚠️ Service temporairement limité. Réessayez demain."
        return {
            **state,
            "answer":     fallback,
            "status":     "token_limit",
            "suggestions": [],
        }
    return state


def node_retrieve(state: RAGState) -> RAGState:
    """
    Nœud 5 — Recherche sémantique ChromaDB
    Adapté depuis Portalyze : ForceRAG.get_response()
    """
    question = state["clean_question"]

    retrieved = retrieve_relevant_docs(question, n_results=5)
    good_docs = [d for d in retrieved if d["score"] >= MIN_CONTEXT_SCORE]
    avg_score = (
        sum(d["score"] for d in good_docs) / len(good_docs)
        if good_docs else 0.0
    )

    if not good_docs:
        lang     = state["language"]
        fallback = DEFAULT_RESPONSES.get(lang, DEFAULT_RESPONSES["french"])
        _track_potential_gap(question, 0.0, fallback, lang)
        sugg = suggest_followup_questions(question, "", lang)
        return {
            **state,
            "retrieved_docs": [],
            "context":        "",
            "avg_score":      0.0,
            "answer":         fallback,
            "suggestions":    sugg,
            "status":         "no_docs",
        }

    context = format_context(good_docs)

    if avg_score < RAG_LACUNE_SEUIL:
        _track_potential_gap(question, avg_score, "", lang=state["language"])

    return {
        **state,
        "retrieved_docs": good_docs,
        "context":        context,
        "avg_score":      avg_score,
    }


def node_generate(state: RAGState) -> RAGState:
    """
    Nœud 6 — Génère la réponse avec le LLM principal
    Adapté depuis Portalyze : ForceRAG.call_groq_llm()
    """
    question  = state["clean_question"]
    context   = state["context"]
    lang      = state["language"]
    sentiment = state["sentiment"]
    history   = state.get("chat_history") or []
    attempt   = state.get("attempt", 0) + 1

    lang_instr = get_language_instruction(lang)
    tone       = sentiment.get("tone_instruction", "")

    full_system = (
        SYSTEM_PROMPT
        + f"\n\n🎭 TON : {tone}"
        + f"\n\n🌍 {lang_instr}"
    )

    # Retry : on rend le prompt plus strict à la 2e tentative
    if attempt > 1:
        full_system += (
            "\n\n🔁 RETRY : La réponse précédente était insuffisante. "
            "Sois plus précis, inclus des chiffres concrets si disponibles."
        )

    messages = [{"role": "system", "content": full_system}]
    for msg in (history or [])[-4:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({
        "role":    "user",
        "content": f"Contexte HoodieWear :\n---\n{context[:2000]}\n---\nQuestion : {question}"
    })

    try:
        response = client.chat.completions.create(
            model=MODEL_MAIN,
            messages=messages,
            temperature=0.3 if attempt == 1 else 0.5,
            max_tokens=400,
        )
        usage = response.usage
        if usage:
            _save_token_usage(usage.total_tokens)
            print(f"🔢 Tokens: {usage.total_tokens} | Total jour: {get_token_usage()['used']}")

        answer = response.choices[0].message.content.strip()

    except Exception as e:
        print(f"❌ Erreur Groq génération: {e}")
        answer = DEFAULT_RESPONSES.get(lang, DEFAULT_RESPONSES["french"])

    return {**state, "answer": answer, "attempt": attempt}


def node_judge(state: RAGState) -> RAGState:
    """
    Nœud 7 — Évalue la réponse générée (LLM-as-a-Judge)
    Adapté depuis Portalyze : JudgeLLM.evaluate()

    Métriques :
      - Faithfulness   : réponse ancrée dans le contexte ?
      - Relevancy      : répond à la question ?
      - Completeness   : réponse suffisamment complète ?
    Score global : moyenne des 3 (0-1)
    """
    question = state["clean_question"]
    answer   = state["answer"]
    context  = state.get("context", "")

    if not context:
        # Pas de contexte RAG → on ne juge pas
        return {**state, "judge_result": {"score": 1.0, "verdict": "skip", "issues": []}}

    judge_prompt = f"""Tu es un évaluateur de qualité pour un chatbot service client (HoodieWear).

QUESTION : {question}

CONTEXTE FOURNI AU CHATBOT :
{context[:1500]}

RÉPONSE DU CHATBOT :
{answer}

Évalue la réponse selon 3 critères (score 0.0 à 1.0 chacun) :
1. faithfulness   : la réponse est-elle fidèle au contexte ? (pas d'hallucination)
2. relevancy      : la réponse répond-elle à la question posée ?
3. completeness   : la réponse est-elle suffisamment complète ?

Réponds UNIQUEMENT avec ce JSON (aucun texte avant/après) :
{{"faithfulness": 0.0, "relevancy": 0.0, "completeness": 0.0, "issues": []}}"""

    try:
        response = client.chat.completions.create(
            model=MODEL_LIGHT,   # Modèle léger pour économiser les tokens
            messages=[{"role": "user", "content": judge_prompt}],
            temperature=0.0,
            max_tokens=150,
        )
        usage = response.usage
        if usage:
            _save_token_usage(usage.total_tokens)

        import re, json
        raw   = response.choices[0].message.content.strip()
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            f = float(parsed.get("faithfulness",  0.5))
            r = float(parsed.get("relevancy",     0.5))
            c = float(parsed.get("completeness",  0.5))
            score  = round((f + r + c) / 3, 3)
            issues = parsed.get("issues", [])
            verdict = "pass" if score >= JUDGE_MIN_SCORE else "fail"
            judge_result = {
                "score":        score,
                "faithfulness": f,
                "relevancy":    r,
                "completeness": c,
                "verdict":      verdict,
                "issues":       issues,
            }
            print(f"⚖️  Judge: score={score} verdict={verdict}")
            return {**state, "judge_result": judge_result}

    except Exception as e:
        print(f"⚠️  Judge LLM échoué: {e} — on laisse passer")

    # Fallback permissif
    return {**state, "judge_result": {"score": 0.7, "verdict": "pass", "issues": []}}


def node_postprocess(state: RAGState) -> RAGState:
    """
    Nœud 8 — Cache + suggestions + learning trigger
    Adapté depuis Portalyze : five_p_agent_node (synthèse finale)
    """
    question  = state["clean_question"]
    answer    = state["answer"]
    lang      = state["language"]
    avg_score = state.get("avg_score", 0.0)
    good_docs = state.get("retrieved_docs", [])

    # Met en cache si score RAG + judge suffisants
    judge = state.get("judge_result", {})
    if avg_score >= 0.5 and judge.get("score", 0) >= JUDGE_MIN_SCORE:
        _save_to_cache(state["cache_key"], answer, good_docs, lang)

    # Suggestions sans LLM
    sugg = suggest_followup_questions(question, answer, lang, good_docs)

    return {
        **state,
        "suggestions": sugg,
        "status":      "done",
    }


# ══════════════════════════════════════════════════════════════════════════════
# ROUTEURS CONDITIONNELS
# ══════════════════════════════════════════════════════════════════════════════

def route_after_escalation(state: RAGState) -> str:
    if state.get("escalation"):
        return "done"
    return "check_cache"


def route_after_cache(state: RAGState) -> str:
    if state.get("from_cache"):
        return "done"
    return "check_token_limit"


def route_after_token(state: RAGState) -> str:
    if state["status"] == "token_limit":
        return "done"
    return "retrieve"


def route_after_retrieve(state: RAGState) -> str:
    if state["status"] == "no_docs":
        return "done"
    return "generate"


def route_after_judge(state: RAGState) -> str:
    """
    Si le juge rejette ET qu'on n'a pas encore dépassé MAX_RETRIES
    → on retente la génération avec un prompt plus strict.
    Sinon → on accepte et on postprocess.
    """
    judge   = state.get("judge_result", {})
    attempt = state.get("attempt", 1)

    if judge.get("verdict") == "fail" and attempt < MAX_RETRIES:
        print(f"🔁 Retry génération (attempt {attempt}/{MAX_RETRIES})...")
        return "generate"
    return "postprocess"


# ══════════════════════════════════════════════════════════════════════════════
# CONSTRUCTION DU GRAPHE
# ══════════════════════════════════════════════════════════════════════════════

def build_rag_graph() -> StateGraph:
    """
    Construit le graphe LangGraph du pipeline RAG HoodieWear.
    Inspiré de Portalyze pipeline.py (build_workflow).
    """
    workflow = StateGraph(RAGState)

    # Enregistrement des nœuds
    workflow.add_node("preprocess",          node_preprocess)
    workflow.add_node("check_escalation",    node_check_escalation)
    workflow.add_node("check_cache",         node_check_cache)
    workflow.add_node("check_token_limit",   node_check_token_limit)
    workflow.add_node("retrieve",            node_retrieve)
    workflow.add_node("generate",            node_generate)
    workflow.add_node("judge",               node_judge)
    workflow.add_node("postprocess",         node_postprocess)

    # Nœud terminal
    workflow.add_node("done", lambda s: s)

    # Flux principal
    workflow.set_entry_point("preprocess")
    workflow.add_edge("preprocess", "check_escalation")

    # Branchements conditionnels
    workflow.add_conditional_edges(
        "check_escalation",
        route_after_escalation,
        {"done": "done", "check_cache": "check_cache"}
    )
    workflow.add_conditional_edges(
        "check_cache",
        route_after_cache,
        {"done": "done", "check_token_limit": "check_token_limit"}
    )
    workflow.add_conditional_edges(
        "check_token_limit",
        route_after_token,
        {"done": "done", "retrieve": "retrieve"}
    )
    workflow.add_conditional_edges(
        "retrieve",
        route_after_retrieve,
        {"done": "done", "generate": "generate"}
    )
    workflow.add_edge("generate", "judge")
    workflow.add_conditional_edges(
        "judge",
        route_after_judge,
        {"generate": "generate", "postprocess": "postprocess"}
    )
    workflow.add_edge("postprocess", "done")
    workflow.add_edge("done", END)

    return workflow.compile()


# Singleton compilé une fois au démarrage
_graph = None

def get_rag_graph():
    global _graph
    if _graph is None:
        _graph = build_rag_graph()
    return _graph


# ══════════════════════════════════════════════════════════════════════════════
# API PUBLIQUE — compatible avec app.py existant
# ══════════════════════════════════════════════════════════════════════════════

def _build_initial_state(question: str, chat_history: list) -> RAGState:
    return RAGState(
        question=question,
        chat_history=chat_history or [],
        clean_question="",
        language="french",
        sentiment={},
        from_cache=False,
        cache_key="",
        retrieved_docs=[],
        context="",
        avg_score=0.0,
        answer="",
        attempt=0,
        judge_result={},
        suggestions=[],
        escalation=False,
        status="ok",
        error=None,
    )


def answer_question_graph(question: str,
                           chat_history: list = None) -> dict:
    """
    Pipeline RAG complet via LangGraph.
    Remplace answer_question() de rag_chain.py

    Retourne le même format de dict pour compatibilité totale avec app.py.
    """
    graph  = get_rag_graph()
    state  = _build_initial_state(question, chat_history)
    result = graph.invoke(state)

    return {
        "answer":       result["answer"],
        "sources":      result.get("retrieved_docs", []),
        "context_used": result.get("context", ""),
        "language":     result.get("language", "french"),
        "sentiment":    result.get("sentiment", {}),
        "suggestions":  result.get("suggestions", []),
        "escalation":   result.get("escalation", False),
        "from_cache":   result.get("from_cache", False),
        "judge":        result.get("judge_result", {}),
        "avg_score":    result.get("avg_score", 0.0),
    }


def answer_question_stream_graph(question: str,
                                  chat_history: list = None) -> dict:
    """
    Version streaming du pipeline LangGraph.
    Remplace answer_question_stream() de rag_chain.py.

    Stratégie : on exécute toutes les étapes pré-génération en LangGraph,
    puis on stream uniquement la génération finale (token par token).
    Compatible avec st.write_stream() de Streamlit.
    """
    # Étapes 1-5 via LangGraph (sans generate)
    graph = get_rag_graph()
    state = _build_initial_state(question, chat_history)

    # Exécution partielle : jusqu'à "retrieve" inclus
    partial = StateGraph(RAGState)
    partial.add_node("preprocess",        node_preprocess)
    partial.add_node("check_escalation",  node_check_escalation)
    partial.add_node("check_cache",       node_check_cache)
    partial.add_node("check_token_limit", node_check_token_limit)
    partial.add_node("retrieve",          node_retrieve)
    partial.add_node("done",              lambda s: s)
    partial.set_entry_point("preprocess")
    partial.add_edge("preprocess", "check_escalation")
    partial.add_conditional_edges("check_escalation", route_after_escalation,
                                   {"done": "done", "check_cache": "check_cache"})
    partial.add_conditional_edges("check_cache", route_after_cache,
                                   {"done": "done", "check_token_limit": "check_token_limit"})
    partial.add_conditional_edges("check_token_limit", route_after_token,
                                   {"done": "done", "retrieve": "retrieve"})
    partial.add_conditional_edges("retrieve", route_after_retrieve,
                                   {"done": "done", "generate": "done"})
    partial.add_edge("done", END)

    pre_graph = partial.compile()
    pre_state = pre_graph.invoke(state)

    lang      = pre_state.get("language", "french")
    sentiment = pre_state.get("sentiment", {})
    status    = pre_state.get("status", "ok")

    # Si résolu avant génération (cache, escalation, no_docs, token_limit)
    if status in ("cache_hit", "escalation", "no_docs", "token_limit"):
        answer = pre_state["answer"]

        def static_stream():
            for word in answer.split(" "):
                yield word + " "

        return {
            "stream":   static_stream(),
            "metadata": {
                "sources":    pre_state.get("retrieved_docs", []),
                "sentiment":  sentiment,
                "language":   lang,
                "escalation": pre_state.get("escalation", False),
                "suggestions": pre_state.get("suggestions", []),
                "from_cache": pre_state.get("from_cache", False),
                "judge":      {},
                "avg_score":  pre_state.get("avg_score", 0.0),
            }
        }

    # Génération streaming (token par token)
    context   = pre_state.get("context", "")
    good_docs = pre_state.get("retrieved_docs", [])
    avg_score = pre_state.get("avg_score", 0.0)
    tone      = sentiment.get("tone_instruction", "")

    full_system = (
        SYSTEM_PROMPT
        + f"\n\n🎭 TON : {tone}"
        + f"\n\n🌍 {get_language_instruction(lang)}"
    )
    messages = [{"role": "system", "content": full_system}]
    for msg in (chat_history or [])[-4:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    clean_q = pre_state.get("clean_question", question)
    messages.append({
        "role":    "user",
        "content": f"Contexte HoodieWear :\n---\n{context[:2000]}\n---\nQuestion : {clean_q}"
    })

    stream = client.chat.completions.create(
        model=MODEL_MAIN,
        messages=messages,
        temperature=0.3,
        max_tokens=400,
        stream=True,
    )

    def token_stream():
        total = 0
        for chunk in stream:
            token = chunk.choices[0].delta.content
            if token is not None:
                total += 1
                yield token
        # Estimation tokens (pas dispo en streaming)
        _save_token_usage(total * 4)

    sugg = suggest_followup_questions(clean_q, "", lang, good_docs)

    return {
        "stream": token_stream(),
        "metadata": {
            "sources":    good_docs,
            "sentiment":  sentiment,
            "language":   lang,
            "escalation": False,
            "suggestions": sugg,
            "from_cache": False,
            "judge":      {},
            "avg_score":  avg_score,
        }
    }


# ══════════════════════════════════════════════════════════════════════════════
# TEST RAPIDE
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Test pipeline RAG LangGraph — HoodieWear")
    print("=" * 60)

    result = answer_question_graph("Quels sont les délais de livraison en Tunisie ?")
    print(f"\n📝 Réponse   : {result['answer'][:120]}...")
    print(f"🌍 Langue    : {result['language']}")
    print(f"📊 Score RAG : {result['avg_score']}")
    print(f"⚖️  Judge     : {result['judge']}")
    print(f"💡 Suggestions: {result['suggestions']}")