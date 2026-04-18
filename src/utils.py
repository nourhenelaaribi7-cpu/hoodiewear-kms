import json
import csv
import os

def load_json_file(filepath):
    """Charge un fichier JSON et retourne une liste de documents texte"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    documents = []
    metadatas = []
    
    for item in data:
        # Combine question + réponse en un seul texte
        text = ""
        if "question" in item:
            text += f"Question: {item['question']}\n"
        if "answer" in item or "reponse" in item:
            answer = item.get("answer", item.get("reponse", ""))
            text += f"Réponse: {answer}"
        
        meta = {
            "source": filepath,
            "tags": str(item.get("tags", [])),
            "keywords": str(item.get("keywords", item.get("mots_cles", [])))
        }
        
        if text.strip():
            documents.append(text.strip())
            metadatas.append(meta)
    
    return documents, metadatas


def load_csv_file(filepath):
    """Charge un fichier CSV"""
    documents = []
    metadatas = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = " | ".join([f"{k}: {v}" for k, v in row.items() if v])
            meta = {"source": filepath}
            documents.append(text)
            metadatas.append(meta)
    
    return documents, metadatas


def load_text_file(filepath):
    """Charge un fichier texte brut (transcriptions Whisper, OCR)"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Découpe en chunks de ~500 caractères avec overlap
    chunks = chunk_text(content, chunk_size=500, overlap=50)
    metadatas = [{"source": filepath} for _ in chunks]
    return chunks, metadatas


def chunk_text(text, chunk_size=500, overlap=50):
    """Découpe un texte long en morceaux avec chevauchement"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def load_all_data(data_folder="data/raw"):
    """Charge tous les fichiers du dossier data/raw"""
    all_docs = []
    all_metas = []
    
    for filename in os.listdir(data_folder):
        filepath = os.path.join(data_folder, filename)
        print(f"Chargement: {filename}")
        
        if filename.endswith(".json"):
            docs, metas = load_json_file(filepath)
        elif filename.endswith(".csv"):
            docs, metas = load_csv_file(filepath)
        elif filename.endswith(".txt"):
            docs, metas = load_text_file(filepath)
        else:
            continue
        
        all_docs.extend(docs)
        all_metas.extend(metas)
    
    print(f"Total documents chargés: {len(all_docs)}")
    return all_docs, all_metas

def chunk_text(text, chunk_size=500, overlap=100):
    """Chunking amélioré avec overlap plus grand"""
    sentences = text.replace('\n', ' ').split('. ')
    chunks = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) < chunk_size:
            current += sentence + ". "
        else:
            if current.strip():
                chunks.append(current.strip())
            current = sentence + ". "
    if current.strip():
        chunks.append(current.strip())
    return chunks if chunks else [text]