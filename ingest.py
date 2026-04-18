import json
from dotenv import load_dotenv

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# Charger variables d'environnement
load_dotenv()

# Charger données
with open("data/data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

texts = [item["text"] for item in data]

# Chunking
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)

docs = splitter.create_documents(texts)

# Embeddings
embedding = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

# Stockage
db = Chroma.from_documents(docs, embedding, persist_directory="db")
db.persist()

print("Vectorisation terminée")