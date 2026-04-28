# src/retriever.py
"""
Retriever amélioré :
  - Suppression de la définition dupliquée de retrieve_relevant_docs (bug corrigé)
  - Filtre de score minimum paramétrable
  - Nouvelle fonction semantic_deduplicate_gaps() pour regrouper
    les lacunes par similarité d'embeddings (remplace le groupement par mots-clés)
  - Hybrid search BM25 + dense (amélioration v2)
"""
from src.indexer import get_collection


def retrieve_relevant_docs(query: str, n_results: int = 5, min_score: float = 0.3):
    """
    Recherche sémantique : retourne les passages les plus pertinents
    pour une question donnée.

    Args:
        query      : question en langage naturel
        n_results  : nombre de résultats à demander à ChromaDB
        min_score  : seuil de similarité cosine minimum (0-1)

    Returns:
        list[dict] avec keys: content, metadata, score
    """
    collection = get_collection()

    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        include=["documents", "metadatas", "distances"]
    )

    docs      = results["documents"][0]
    metas     = results["metadatas"][0]
    distances = results["distances"][0]

    retrieved = []
    for doc, meta, dist in zip(docs, metas, distances):
        score = round(1 - dist, 3)          # distance cosine → similarité
        if score >= min_score:
            retrieved.append({
                "content":  doc,
                "metadata": meta,
                "score":    score
            })

    return retrieved


def format_context(retrieved_docs: list) -> str:
    """Formate les documents récupérés en contexte pour le LLM."""
    context = ""
    for i, doc in enumerate(retrieved_docs, 1):
        context += f"[Document {i}] (score: {doc['score']})\n"
        context += doc["content"] + "\n\n"
    return context.strip()


# ── Déduplication sémantique des gaps ─────────────────────────────────────────
def semantic_deduplicate_gaps(gaps: list, threshold: float = 0.82) -> list:
    """
    Regroupe les lacunes sémantiquement similaires en utilisant ChromaDB.

    Compare chaque gap avec les gaps DÉJÀ RETENUS (et non avec la FAQ),
    ce qui évite le faux positif de déduplication.

    Algorithme :
      1. On maintient une liste temporaire "seen_questions" (questions déjà retenues).
      2. Pour chaque nouveau gap, on interroge ChromaDB avec sa question.
      3. Si un des tops résultats est une question déjà retenue avec score >= threshold,
         on considère le gap comme doublon.
      4. Sinon on le conserve et on l'ajoute à seen_questions.

    Returns:
        list : sous-ensemble de gaps avec les doublons sémantiques retirés.
    """
    collection = get_collection()
    unique_gaps = []
    seen_questions = []

    for gap in gaps:
        question = gap.get("question", "").strip()
        if not question:
            continue

        is_duplicate = False

        if seen_questions:
            try:
                # On interroge ChromaDB avec la question du gap courant
                results = collection.query(
                    query_texts=[question],
                    n_results=3,
                    include=["documents", "distances"]
                )
                if results["distances"] and results["distances"][0]:
                    for i, dist in enumerate(results["distances"][0]):
                        score = round(1 - dist, 3)
                        doc_text = results["documents"][0][i] if results["documents"][0] else ""
                        # On vérifie si ce résultat correspond à une question déjà retenue
                        for seen_q in seen_questions:
                            if seen_q.lower() in doc_text.lower() and score >= threshold:
                                is_duplicate = True
                                break
                        if is_duplicate:
                            break
            except Exception:
                pass    # En cas d'erreur on garde le gap

        if not is_duplicate:
            unique_gaps.append(gap)
            seen_questions.append(question)

    return unique_gaps


def get_avg_score_for_query(query: str, n_results: int = 3) -> float:
    """
    Retourne le score RAG moyen pour une requête donnée.
    Utilisé par la boucle de validation post-correction.
    """
    docs = retrieve_relevant_docs(query, n_results=n_results, min_score=0.0)
    if not docs:
        return 0.0
    return round(sum(d["score"] for d in docs) / len(docs), 3)


# ── Hybrid search BM25 + dense ─────────────────────────────────────────────────
def hybrid_retrieve(query: str, all_docs: list,
                    n_results: int = 5, alpha: float = 0.6):
    """
    Retrieval hybride : alpha * dense_score + (1-alpha) * bm25_score
    alpha=0.6 → 60% sémantique, 40% lexical

    Args:
        query     : question en langage naturel
        all_docs  : liste de tous les textes de documents (strings)
        n_results : nombre de résultats à retourner
        alpha     : pondération du score dense (0 = BM25 pur, 1 = dense pur)

    Returns:
        list[dict] avec keys: content, score
    """
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        # Fallback si rank-bm25 n'est pas installé
        print("⚠️  rank-bm25 non installé. Utilisation du retrieval dense uniquement.")
        return retrieve_relevant_docs(query, n_results=n_results)

    if not all_docs:
        return retrieve_relevant_docs(query, n_results=n_results)

    # Score dense (ChromaDB)
    dense_results = retrieve_relevant_docs(query, n_results=n_results * 2, min_score=0.0)
    dense_map = {d["content"]: d["score"] for d in dense_results}

    # Score BM25
    tokenized_docs  = [d.lower().split() for d in all_docs]
    bm25            = BM25Okapi(tokenized_docs)
    query_tokens    = query.lower().split()
    bm25_scores     = bm25.get_scores(query_tokens)

    # Normalisation BM25 entre 0 et 1
    max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1
    bm25_norm = [s / max_bm25 for s in bm25_scores]

    # Score combiné
    combined = []
    for i, doc in enumerate(all_docs):
        dense  = dense_map.get(doc, 0)
        bm25_s = bm25_norm[i] if i < len(bm25_norm) else 0
        score  = alpha * dense + (1 - alpha) * bm25_s
        if score > 0.25:
            combined.append({"content": doc, "score": round(score, 3), "metadata": {}})

    combined.sort(key=lambda x: x["score"], reverse=True)
    return combined[:n_results]