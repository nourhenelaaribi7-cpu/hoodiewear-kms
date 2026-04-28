"""
Processeur audio temps réel — HoodieWear KMS
Simule la transcription d'un message vocal client via Whisper (Groq)
"""
import os
import json
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def transcribe_audio_file(audio_path: str, language: str = "fr") -> str:
    """
    Transcrit un fichier audio avec Whisper via Groq.
    Supporte : mp3, mp4, wav, m4a, ogg, flac
    """
    with open(audio_path, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=f,
            language=language
        )
    return result.text


def process_audio_to_knowledge(audio_path: str,
                                 category: str = "support_client",
                                 language: str = "fr") -> dict:
    """
    Pipeline complet : Audio → Transcription → Indexation ChromaDB
    
    Utilisé pour :
    - Enregistrements appels service client
    - Vidéos formation agents  
    - Messages vocaux clients (futur)
    """
    print(f"🎙️ Transcription de : {audio_path}")
    
    # 1. Transcription Whisper
    transcription = transcribe_audio_file(audio_path, language)
    print(f"✅ Transcription : {transcription[:100]}...")
    
    # 2. Sauvegarde JSON
    entry = {
        "id":         f"audio_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "question":   transcription,
        "reponse":    "",  # À remplir manuellement ou par le LLM
        "source":     "whisper_realtime",
        "audio_file": os.path.basename(audio_path),
        "category":   category,
        "langue":     language,
        "date":       datetime.now().strftime("%Y-%m-%d %H:%M"),
        "tags":       [category, language],
        "mots_cles":  transcription.lower().split()[:5]
    }
    
    # 3. Sauvegarde dans data/raw
    output_file = "data/raw/audio_realtime.json"
    os.makedirs("data/raw", exist_ok=True)
    
    existing = []
    if os.path.exists(output_file):
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []
    
    existing.append(entry)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    
    # 4. Indexation directe dans ChromaDB
    from src.indexer import get_collection
    collection = get_collection()
    
    doc_text = f"Question/Contenu audio: {transcription}"
    doc_id   = f"audio_{entry['id']}"
    
    collection.add(
        documents=[doc_text],
        metadatas=[{
            "source":   output_file,
            "tags":     str(entry["tags"]),
            "keywords": str(entry["mots_cles"]),
            "type":     "audio_transcription"
        }],
        ids=[doc_id]
    )
    
    print(f"✅ Indexé dans ChromaDB : {doc_id}")
    return entry


def get_audio_stats() -> dict:
    """Statistiques sur les fichiers audio traités"""
    output_file = "data/raw/audio_realtime.json"
    
    if not os.path.exists(output_file):
        return {"total": 0, "categories": {}, "languages": {}}
    
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            entries = json.load(f)
    except Exception:
        return {"total": 0, "categories": {}, "languages": {}}
    
    categories = {}
    languages  = {}
    
    for e in entries:
        cat  = e.get("category", "autre")
        lang = e.get("langue", "fr")
        categories[cat]  = categories.get(cat, 0) + 1
        languages[lang]  = languages.get(lang, 0) + 1
    
    return {
        "total":      len(entries),
        "categories": categories,
        "languages":  languages
    }
