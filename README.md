# 👕 HoodieWear Smart KMS

Système de support client intelligent basé sur RAG + LLM.

## Stack technique
- 🧠 LLM : Llama 3.3 70B via Groq API (gratuit)
- 🔍 RAG : ChromaDB (base vectorielle locale)
- 📐 Embeddings : all-MiniLM-L6-v2 (sentence-transformers)
- 🖥️ UI : Streamlit multipage

## Installation
```bash
python -m venv rag_env
rag_env\Scripts\activate
pip install -r requirements.txt
```

## Configuration
Crée un fichier `.env` :