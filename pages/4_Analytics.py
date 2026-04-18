import streamlit as st
import json
import os
import pandas as pd
from collections import Counter

st.set_page_config(page_title="Analytics", page_icon="🔬", layout="wide")
st.title("🔬 Analytics Avancées — HoodieWear KMS")
st.divider()

FEEDBACK_FILE = "data/feedback.json"
HISTORY_FILE  = "data/historique.json"

# Chargement sécurisé
feedbacks, history = [], []
for fpath, lst in [(FEEDBACK_FILE, feedbacks), (HISTORY_FILE, history)]:
    if os.path.exists(fpath):
        try:
            content = open(fpath, encoding="utf-8").read().strip()
            lst += json.loads(content) if content else []
        except: pass

# ── Mots-clés les plus fréquents ─────────────────────────────────────────────
st.subheader("🔑 Mots-clés les plus fréquents")
all_questions = [
    msg["content"]
    for conv in history
    for msg in conv["messages"]
    if msg["role"] == "user"
]

if all_questions:
    stopwords = {"comment", "puis", "je", "mon", "ma", "les", "des", "est", "un", "une", "le", "la"}
    words = []
    for q in all_questions:
        words += [w.lower() for w in q.split() if len(w) > 3 and w.lower() not in stopwords]
    
    top_words = Counter(words).most_common(15)
    df_words = pd.DataFrame(top_words, columns=["Mot", "Fréquence"])
    st.bar_chart(df_words.set_index("Mot"))
else:
    st.info("Pas encore de questions posées.")

st.divider()

# ── Taux de satisfaction par jour ────────────────────────────────────────────
st.subheader("📅 Satisfaction par jour")
if feedbacks:
    df = pd.DataFrame(feedbacks)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["ok"] = df["rating"] == "positive"
    daily = df.groupby("date")["ok"].agg(["sum", "count"])
    daily["taux"] = (daily["sum"] / daily["count"] * 100).round(1)
    st.bar_chart(daily["taux"])
else:
    st.info("Pas encore de feedbacks.")

st.divider()

# ── Export CSV ────────────────────────────────────────────────────────────────
st.subheader("📥 Exporter les données")
col1, col2 = st.columns(2)

with col1:
    if feedbacks:
        df_fb = pd.DataFrame(feedbacks)
        csv = df_fb.to_csv(index=False, encoding="utf-8")
        st.download_button("⬇️ Exporter Feedbacks CSV", csv, 
                          "feedbacks.csv", "text/csv", use_container_width=True)

with col2:
    if all_questions:
        df_q = pd.DataFrame({"question": all_questions})
        csv2 = df_q.to_csv(index=False, encoding="utf-8")
        st.download_button("⬇️ Exporter Questions CSV", csv2,
                          "questions.csv", "text/csv", use_container_width=True)