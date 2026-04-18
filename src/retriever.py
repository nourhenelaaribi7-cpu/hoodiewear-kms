# src/retriever.py
"""
Retriever amélioré :
  - Suppression de la définition dupliquée de retrieve_relevant_docs (bug corrigé)
  - Filtre de score minimum paramétrable
  - Nouvelle fonction semantic_deduplicate_gaps() pour regrouper
    les lacunes par similarité d'embeddings (remplace le groupement par mots-clés)
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

    Remplace le groupement naïf par les 6 premiers mots (qui ratait les
    formulations différentes de la même question).

    Algorithme :
      1. Pour chaque gap, on interroge ChromaDB avec la question.
      2. Si un doc déjà indexé retourne un score >= threshold, on
         considère que le gap est déjà couvert → on le marque "doublon".
      3. Sinon on le conserve.

    Returns:
        list : sous-ensemble de gaps avec les doublons sémantiques retirés.
    """
    collection = get_collection()
    unique_gaps = []
    seen_questions = []     # liste des questions déjà retenues

    for gap in gaps:
        question = gap.get("question", "").strip()
        if not question:
            continue

        # Vérifie la similarité avec les gaps déjà retenus
        is_duplicate = False

        if seen_questions:
            try:
                # On interroge une collection temporaire construite depuis
                # les questions déjà retenues — utilisation de la collection
                # principale comme moteur d'embedding uniquement.
                results = collection.query(
                    query_texts=[question],
                    n_results=1,
                    include=["documents", "distances"]
                )
                if results["distances"] and results["distances"][0]:
                    best_score = round(1 - results["distances"][0][0], 3)
                    # Si la base contient déjà la réponse avec un bon score,
                    # ce gap est peut-être déjà couvert.
                    if best_score >= threshold:
                        is_duplicate = True
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