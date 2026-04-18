import streamlit as st
import json
import os

st.set_page_config(page_title="Statistiques", page_icon="📊", layout="wide")

st.title("📊 Statistiques — HoodieWear KMS")
st.divider()

FEEDBACK_FILE = "data/feedback.json"
HISTORY_FILE  = "data/historique.json"

# ── Chargement sécurisé ───────────────────────────────────────────────────────
feedbacks = []
if os.path.exists(FEEDBACK_FILE):
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            feedbacks = json.loads(content) if content else []
    except (json.JSONDecodeError, Exception):
        feedbacks = []

history = []
if os.path.exists(HISTORY_FILE):
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            history = json.loads(content) if content else []
    except (json.JSONDecodeError, Exception):
        history = []

# ── Métriques globales ────────────────────────────────────────────────────────
positifs = [f for f in feedbacks if f["rating"] == "positive"]
negatifs = [f for f in feedbacks if f["rating"] == "negative"]
taux_sat = (len(positifs) / len(feedbacks) * 100) if feedbacks else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total conversations", len(history))
c2.metric("Total feedbacks",     len(feedbacks))
c3.metric("👍 Satisfaction",     f"{taux_sat:.0f}%")
c4.metric("👎 À améliorer",      len(negatifs))

st.divider()

# ── Graphique satisfaction ────────────────────────────────────────────────────
if feedbacks:
    st.subheader("📈 Évolution de la satisfaction")
    
    import pandas as pd
    df = pd.DataFrame(feedbacks)
    df["date"] = pd.to_datetime(df["date"])
    df["positif"] = df["rating"] == "positive"
    
    daily = df.groupby(df["date"].dt.date)["positif"].mean() * 100
    st.line_chart(daily, y_label="% satisfaction", x_label="Date")
    
    st.divider()
    st.subheader("📋 Détail des feedbacks")
    st.dataframe(
        df[["date", "question", "rating"]].rename(columns={
            "date": "Date",
            "question": "Question",
            "rating": "Évaluation"
        }),
        use_container_width=True
    )
else:
    st.info("Pas encore de données de feedback. Commencez à utiliser le chat !")

st.divider()

# ── Questions les plus posées ─────────────────────────────────────────────────
if history:
    st.subheader("🔥 Questions posées en session")
    all_questions = []
    for conv in history:
        for msg in conv["messages"]:
            if msg["role"] == "user":
                all_questions.append(msg["content"])
    
    if all_questions:
        import pandas as pd
        df_q = pd.DataFrame({"Question": all_questions})
        st.dataframe(df_q, use_container_width=True)
else:
    st.info("Aucune conversation dans l'historique pour le moment.")