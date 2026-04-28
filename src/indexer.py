import chromadb
from chromadb.utils import embedding_functions
import os
from dotenv import load_dotenv
from src.utils import load_all_data

load_dotenv()

CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "hoodiewear_knowledge"


def get_collection():
    """Retourne la collection ChromaDB avec embeddings locaux"""
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    # sentence-transformers local — gratuit, rapide, pas de limite
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"}
    )
    return collection


def index_documents(data_folder="data/raw"):
    """Charge les données et les indexe dans ChromaDB"""
    collection = get_collection()

    existing = collection.count()
    if existing > 0:
        print(f"Collection déjà indexée avec {existing} documents.")
        response = input("Réindexer ? (o/n): ")
        if response.lower() != 'o':
            return collection
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        client.delete_collection(COLLECTION_NAME)
        collection = get_collection()

    documents, metadatas = load_all_data(data_folder)

    if not documents:
        print("Aucun document trouvé dans data/raw/")
        return collection

    # Indexation par batch de 50
    batch_size = 50
    for i in range(0, len(documents), batch_size):
        batch_docs  = documents[i:i+batch_size]
        batch_metas = metadatas[i:i+batch_size]
        batch_ids   = [f"doc_{i+j}" for j in range(len(batch_docs))]

        collection.add(
            documents=batch_docs,
            metadatas=batch_metas,
            ids=batch_ids
        )
        print(f"Indexé : {min(i+batch_size, len(documents))}/{len(documents)}")

    print(f"\n✅ Indexation terminée : {collection.count()} documents dans ChromaDB")
    return collection


if __name__ == "__main__":
    index_documents()