# pages/1_Admin.py — Version 2.0 avec alertes de régression et Correction Rate
import streamlit as st
import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.indexer import index_documents, get_collection

st.set_page_config(page_title="Administration", page_icon="⚙️", layout="wide")

FEEDBACK_FILE   = "data/feedback.json"
GAP_FAQ_FILE    = "data/raw/faq_auto_generated.json"
REGRESSION_FILE = "data/ragas_regression_alerts.json"

st.title("⚙️ Administration — HoodieWear KMS v3.0")
st.divider()

# ── Alertes de régression RAGAS (nouvelle section) ────────────────────────────
try:
    from src.validator import load_regression_alerts
    regression_alerts = load_regression_alerts()
    # On n'affiche que les alertes récentes (48h)
    from datetime import datetime, timedelta
    recent_alerts = []
    for a in regression_alerts[-10:]:
        try:
            alert_date = datetime.strptime(a["date"], "%Y-%m-%d %H:%M")
            if datetime.now() - alert_date < timedelta(hours=48):
                recent_alerts.append(a)
        except Exception:
            pass

    if recent_alerts:
        st.error(
            f"🚨 **{len(recent_alerts)} régression(s) RAGAS détectée(s) dans les dernières 48h** — "
            f"Consultez la page Évaluation pour les détails."
        )
        for a in recent_alerts:
            st.warning(
                f"📉 **{a['metric']}** : {a['previous']} → {a['current']} "
                f"(↓ {a['drop_pct']}%) | {a['severity'].upper()}"
            )
        st.divider()
except ImportError:
    pass

# ── Section 1 : Upload de fichiers ────────────────────────────────────────────
st.subheader("📁 Ajouter des documents à la base")
st.caption("Formats acceptés : JSON, CSV, TXT")

uploaded_files = st.file_uploader(
    "Glissez vos fichiers ici",
    type=["json", "csv", "txt"],
    accept_multiple_files=True
)

if uploaded_files:
    saved = []
    for file in uploaded_files:
        save_path = os.path.join("data/raw", file.name)
        os.makedirs("data/raw", exist_ok=True)
        with open(save_path, "wb") as f:
            f.write(file.read())
        saved.append(file.name)
    st.success(f"✅ {len(saved)} fichier(s) uploadé(s) : {', '.join(saved)}")

    if st.button("🔄 Réindexer maintenant", type="primary"):
        with st.spinner("Indexation en cours..."):
            try:
                index_documents()
                st.success("✅ Base réindexée avec succès !")
                st.balloons()
            except Exception as e:
                st.error(f"Erreur : {e}")

st.divider()

# ── Section 2 : État de la base ───────────────────────────────────────────────
st.subheader("📊 État de la base de connaissances")

col1, col2, col3, col4, col5 = st.columns(5)

try:
    collection = get_collection()
    count      = collection.count()
    raw_files  = os.listdir("data/raw") if os.path.exists("data/raw") else []

    auto_docs = []
    if os.path.exists(GAP_FAQ_FILE):
        try:
            with open(GAP_FAQ_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                auto_docs = json.loads(content) if content else []
        except Exception:
            pass

    feedbacks = []
    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                feedbacks = json.loads(content) if content else []
        except Exception:
            pass

    positifs = len([f for f in feedbacks if f["rating"] == "positive"])

    with col1:
        st.metric("Documents indexés", count)
    with col2:
        st.metric("Fichiers sources", len(raw_files))
    with col3:
        st.metric("Feedbacks positifs", f"{positifs}/{len(feedbacks)}")
    with col4:
        st.metric("🤖 Docs auto-générés", len(auto_docs))

    # Correction Rate (nouveau)
    with col5:
        try:
            from src.knowledge_gap import get_correction_rate
            cr = get_correction_rate()
            st.metric(
                "🎯 Correction Rate",
                f"{cr['correction_rate']:.0f}%",
                delta=f"{cr['nb_corrected']}/{cr['nb_attempted']}",
                help="% de lacunes réellement corrigées (score RAG amélioré après indexation)"
            )
        except Exception:
            st.metric("🎯 Correction Rate", "N/A")

    st.markdown("**Fichiers dans `data/raw/` :**")
    for fname in raw_files:
        fpath = os.path.join("data/raw", fname)
        size  = os.path.getsize(fpath)
        icon  = "🤖" if "auto_generated" in fname else "📄"
        st.markdown(f"- {icon} `{fname}` ({size/1024:.1f} KB)")

except Exception as e:
    st.error(f"Erreur ChromaDB : {e}")

st.divider()

# ── Section 3 : Feedbacks ──────────────────────────────────────────────────────
st.subheader("💬 Analyse des feedbacks")

feedbacks = []
if os.path.exists(FEEDBACK_FILE):
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            feedbacks = json.loads(content) if content else []
    except Exception:
        pass

if feedbacks:
    positifs = [f for f in feedbacks if f["rating"] == "positive"]
    negatifs = [f for f in feedbacks if f["rating"] == "negative"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Total feedbacks", len(feedbacks))
    c2.metric("👍 Positifs",     len(positifs))
    c3.metric("👎 Négatifs",     len(negatifs))

    if feedbacks:
        taux = len(positifs) / len(feedbacks) * 100
        st.progress(taux / 100, text=f"Satisfaction : {taux:.0f}%")

    st.markdown("**Derniers feedbacks négatifs :**")
    for fb in negatifs[-5:]:
        with st.expander(f"❌ {fb['date']} — {fb['question'][:60]}..."):
            st.write(f"**Question :** {fb['question']}")
            st.write(f"**Réponse donnée :** {fb['answer']}")
            if st.button("🧠 Traiter cette lacune →",
                         key=f"goto_kg_{fb['date']}"):
                st.switch_page("pages/7_KnowledgeGap.py")
else:
    st.info("Aucun feedback reçu pour le moment.")

st.divider()

# ── Section 4 : Actions ───────────────────────────────────────────────────────
st.subheader("🛠️ Actions")

col_a, col_b, col_c, col_d = st.columns(4)
with col_a:
    if st.button("🔄 Réindexer toute la base", use_container_width=True, type="primary"):
        with st.spinner("Réindexation..."):
            try:
                index_documents()
                st.success("✅ Réindexation terminée !")
            except Exception as e:
                st.error(f"Erreur : {e}")
with col_b:
    if st.button("🗑️ Vider les feedbacks", use_container_width=True):
        if os.path.exists(FEEDBACK_FILE):
            os.remove(FEEDBACK_FILE)
            st.success("Feedbacks supprimés !")
            st.rerun()
with col_c:
    if st.button("🧠 Analyser les lacunes", use_container_width=True):
        st.switch_page("pages/7_KnowledgeGap.py")
with col_d:
    if st.button("🔬 Lancer l'évaluation RAGAS", use_container_width=True):
        st.switch_page("pages/5_Evaluation.py")