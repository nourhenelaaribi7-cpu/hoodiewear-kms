import os
import chromadb

def get_chroma_client():
    # Sur Streamlit Cloud, utilise le dossier /tmp
    if os.environ.get("STREAMLIT_SHARING_MODE"):
        return chromadb.PersistentClient(path="/tmp/chroma_db")
    return chromadb.PersistentClient(path="chroma_db")