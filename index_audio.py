"""
index_audio.py
==============
Indexe les transcriptions audio (générées par generate_audio.py)
dans ChromaDB via LangChain.

Embeddings : HuggingFace (gratuit, sans clé API)
VectorStore : ChromaDB local

Usage:
    python index_audio.py                  # Indexe uniquement les nouveaux
    python index_audio.py --reindex        # Force la ré-indexation complète
    python index_audio.py --test-query "livraison"
"""

import json
import logging
import argparse
import hashlib
import sys
from pathlib import Path
from datetime import datetime
from typing import Any

# LangChain
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

DEFAULT_INPUT_PATH  = "data/raw/transcriptions_whisper.json"
CHROMA_PERSIST_DIR  = "chroma_db"
CHROMA_COLLECTION   = "audio_transcriptions"

# Modèle HuggingFace multilingue (français inclus) — téléchargé automatiquement
EMBEDDING_MODEL     = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

LOG_FORMAT  = "%(asctime)s | %(levelname)-8s | %(message)s"
LOG_DATE    = "%Y-%m-%d %H:%M:%S"


# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────

logging.basicConfig(format=LOG_FORMAT, datefmt=LOG_DATE, level=logging.INFO)
logger = logging.getLogger("index_audio")


# ──────────────────────────────────────────────
# Utilitaires
# ──────────────────────────────────────────────

def compute_doc_id(entry: dict[str, Any]) -> str:
    unique_str = f"{entry.get('id', '')}::{entry.get('question', '')}"
    return hashlib.sha256(unique_str.encode()).hexdigest()[:16]


def load_transcriptions(path: str) -> list[dict[str, Any]]:
    file = Path(path)
    if not file.exists():
        logger.error(f"Fichier introuvable : {path}")
        logger.error(f"Lance d'abord : python generate_audio.py")
        sys.exit(1)

    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)

    entries = data if isinstance(data, list) else []
    logger.info(f"📂  {len(entries)} transcription(s) chargée(s) depuis {path}")
    return entries


def build_document(entry: dict[str, Any], doc_id: str) -> Document:
    question = entry.get("question", "").strip()
    reponse  = entry.get("reponse", "").strip()

    if not question:
        raise ValueError(f"Question vide pour l'entrée id={doc_id}")

    text = f"Question: {question}\nRéponse: {reponse}" if reponse else question

    tags = entry.get("tags", [])
    tags_str = ", ".join(tags) if isinstance(tags, list) else str(tags)

    metadata = {
        "doc_id":     doc_id,
        "entry_id":   entry.get("id", "unknown"),
        "intent":     entry.get("intent", "unknown"),
        "tags":       tags_str,
        "langue":     entry.get("langue", "fr"),
        "source":     entry.get("source", "whisper_transcription"),
        "methode":    entry.get("methode", "whisper-large-v3"),
        "indexed_at": datetime.utcnow().isoformat(),
    }

    return Document(page_content=text, metadata=metadata)


def get_existing_ids(vectorstore: Chroma) -> set[str]:
    try:
        results = vectorstore.get(include=["metadatas"])
        ids = {
            meta.get("doc_id")
            for meta in results.get("metadatas", [])
            if meta.get("doc_id")
        }
        logger.info(f"🗃️   {len(ids)} document(s) déjà indexé(s) dans ChromaDB")
        return ids
    except Exception as exc:
        logger.warning(f"Impossible de lire les IDs existants : {exc}")
        return set()


# ──────────────────────────────────────────────
# Pipeline principal
# ──────────────────────────────────────────────

def run_indexing(input_path: str = DEFAULT_INPUT_PATH, reindex: bool = False) -> None:
    logger.info("=" * 60)
    logger.info("🚀  Démarrage de l'indexation audio → ChromaDB")
    logger.info("=" * 60)

    entries = load_transcriptions(input_path)

    logger.info(f"🔧  Chargement du modèle : {EMBEDDING_MODEL}")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    logger.info("✅  Modèle chargé")

    logger.info(f"🗄️   ChromaDB → {CHROMA_PERSIST_DIR} / {CHROMA_COLLECTION}")
    vectorstore = Chroma(
        collection_name=CHROMA_COLLECTION,
        embedding_function=embeddings,
        persist_directory=CHROMA_PERSIST_DIR,
    )

    existing_ids: set[str] = set() if reindex else get_existing_ids(vectorstore)

    documents: list[Document] = []
    skipped = 0
    errors  = 0

    for entry in entries:
        doc_id = compute_doc_id(entry)

        if doc_id in existing_ids:
            skipped += 1
            continue

        try:
            doc = build_document(entry, doc_id)
            documents.append(doc)
        except ValueError as exc:
            errors += 1
            logger.warning(f"⚠️  {exc}")

    logger.info(f"📊  À indexer: {len(documents)} | Ignorés: {skipped} | Erreurs: {errors}")

    if not documents:
        logger.info("✅  Aucun nouveau document. Base déjà à jour.")
        return

    ids = [doc.metadata["doc_id"] for doc in documents]
    vectorstore.add_documents(documents=documents, ids=ids)

    try:
        vectorstore.persist()
    except AttributeError:
        pass

    logger.info("=" * 60)
    logger.info(f"🎉  Terminé ! {len(documents)} nouveaux | {skipped} ignorés")
    logger.info(f"     📁 ChromaDB : {Path(CHROMA_PERSIST_DIR).resolve()}")
    logger.info("=" * 60)


def test_query(query: str) -> None:
    logger.info(f"\n🔍  Test : '{query}'")

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    vectorstore = Chroma(
        collection_name=CHROMA_COLLECTION,
        embedding_function=embeddings,
        persist_directory=CHROMA_PERSIST_DIR,
    )

    results = vectorstore.similarity_search(query, k=3)

    for i, doc in enumerate(results, 1):
        logger.info(f"\n  ── Résultat #{i} ──")
        logger.info(f"  {doc.page_content[:200]}")
        logger.info(f"  Intent : {doc.metadata.get('intent')} | Tags : {doc.metadata.get('tags')}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",      default=DEFAULT_INPUT_PATH)
    parser.add_argument("--reindex",    action="store_true")
    parser.add_argument("--test-query", metavar="QUERY")
    parser.add_argument("--verbose",    action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    run_indexing(input_path=args.input, reindex=args.reindex)

    if args.test_query:
        test_query(args.test_query)