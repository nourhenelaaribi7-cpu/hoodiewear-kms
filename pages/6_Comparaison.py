# pages/6_Comparaison.py
import streamlit as st
import sys
import os
import time
from src.auth import require_agent_or_admin
user = require_agent_or_admin()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag_chain import answer_question, call_groq_llm

st.set_page_config(page_title="RAG vs Sans RAG", page_icon="⚖️", layout="wide")

st.title("⚖️ Comparaison — RAG vs Sans RAG")
st.caption("Démonstration concrète de l'apport du système RAG par rapport à un LLM seul.")
st.divider()
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/icon?family=Material+Icons+Round" rel="stylesheet">

<style>
/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
}
.stApp {
    background: linear-gradient(135deg, #0f0c29 0%, #141428 50%, #0f0c29 100%);
    color: #e8e6f0;
    min-height: 100vh;
}
.block-container {
    padding-top: 2rem;
    max-width: 1200px;
    position: relative;
    z-index: 1;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: rgba(15, 12, 41, 0.95) !important;
    border-right: 1px solid rgba(167, 139, 250, 0.15) !important;
}
[data-testid="stSidebar"] * {
    color: #c4b5fd !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span {
    color: #c4b5fd !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
}
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
    color: #a78bfa !important;
    font-size: 0.9rem !important;
    font-weight: 600 !important;
    padding: 0.5rem 1rem !important;
    border-radius: 8px !important;
    transition: background 0.2s !important;
}
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {
    background: rgba(167, 139, 250, 0.12) !important;
}
[data-testid="stSidebar"] hr {
    border-color: rgba(167, 139, 250, 0.2) !important;
}

/* ── All text elements — lisibilité maximale ── */
h1, h2, h3, h4, p, span, div, label, li {
    color: #f0eeff;
}
.stMarkdown p {
    color: #d4cfee !important;
    font-size: 0.95rem !important;
    line-height: 1.7 !important;
}
.stMarkdown strong {
    color: #f5f3ff !important;
    font-weight: 700 !important;
}
.stCaption, [data-testid="stCaptionContainer"] p {
    color: #7c77a0 !important;
    font-size: 0.8rem !important;
}
.stAlert p, [data-testid="stAlert"] p {
    color: #1a1a2e !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
}

/* ── Form labels ── */
[data-testid="stForm"] label,
.stTextArea label,
.stTextInput label,
.stToggle label {
    color: #a78bfa !important;
    font-size: 0.78rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
}

/* ── Inputs & Textareas ── */
.stTextArea textarea,
.stTextInput input {
    background: rgba(255, 255, 255, 0.05) !important;
    border: 1px solid rgba(167, 139, 250, 0.25) !important;
    border-radius: 10px !important;
    color: #f0eeff !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.92rem !important;
    line-height: 1.6 !important;
    caret-color: #a78bfa !important;
}
.stTextArea textarea:focus,
.stTextInput input:focus {
    border-color: rgba(167, 139, 250, 0.6) !important;
    box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.1) !important;
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #7c3aed, #4f46e5) !important;
    border: none !important;
    border-radius: 10px !important;
    color: #ffffff !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.9rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.02em !important;
    padding: 0.65rem 1.4rem !important;
    transition: opacity 0.2s, transform 0.15s !important;
}
.stButton > button:hover {
    opacity: 0.9 !important;
    transform: translateY(-1px) !important;
}
.stFormSubmitButton > button {
    background: linear-gradient(135deg, #7c3aed, #4f46e5) !important;
    border: none !important;
    border-radius: 10px !important;
    color: #ffffff !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.92rem !important;
    font-weight: 700 !important;
    padding: 0.65rem 1.4rem !important;
    width: 100% !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: rgba(255, 255, 255, 0.03) !important;
    border: 1px solid rgba(167, 139, 250, 0.15) !important;
    border-radius: 12px !important;
    margin-bottom: 8px !important;
}
[data-testid="stExpander"] summary {
    color: #d4cfee !important;
    font-size: 0.9rem !important;
    font-weight: 600 !important;
    padding: 0.8rem 1rem !important;
}
[data-testid="stExpander"] summary:hover {
    background: rgba(167, 139, 250, 0.06) !important;
    border-radius: 12px !important;
}

/* ── Metrics (st.metric) ── */
[data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.04) !important;
    border: 1px solid rgba(167, 139, 250, 0.15) !important;
    border-radius: 12px !important;
    padding: 1rem !important;
}
[data-testid="stMetricLabel"] p {
    color: #7c77a0 !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
}
[data-testid="stMetricValue"] {
    color: #c4b5fd !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 1.6rem !important;
    font-weight: 700 !important;
}

/* ── Divider ── */
hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, rgba(167,139,250,0.2) 30%, rgba(167,139,250,0.2) 70%, transparent) !important;
    margin: 2rem 0 !important;
}

/* ── Spinner ── */
.stSpinner p {
    color: #a78bfa !important;
    font-size: 0.88rem !important;
}

/* ── Info / Warning / Error boxes ── */
[data-testid="stAlert"][data-baseweb="notification"] {
    border-radius: 10px !important;
    border-left-width: 4px !important;
}

/* ── Toggle ── */
[data-testid="stToggle"] span {
    color: #d4cfee !important;
    font-size: 0.9rem !important;
}

/* ── Line chart ── */
.stVegaLiteChart, .stArrowVegaLiteChart {
    background: rgba(255,255,255,0.02) !important;
    border-radius: 12px !important;
    padding: 1rem !important;
    border: 1px solid rgba(167, 139, 250, 0.12) !important;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }

/* ══ Custom components ══ */

/* Page header */
.page-header {
    padding: 2rem 0 1.8rem;
    margin-bottom: 2rem;
    position: relative;
}
.page-header::after {
    content: '';
    position: absolute;
    bottom: 0; left: 0;
    width: 60px; height: 3px;
    background: linear-gradient(90deg, #a78bfa, #60a5fa);
    border-radius: 2px;
}
.eyebrow {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #a78bfa;
    margin-bottom: 0.6rem;
    display: flex; align-items: center; gap: 0.5rem;
}
.eyebrow::before {
    content: '';
    display: inline-block;
    width: 18px; height: 2px;
    background: #a78bfa;
    border-radius: 1px;
}
.page-title {
    font-size: 3rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    color: #f5f3ff;
    margin: 0 0 0.4rem;
    line-height: 1;
    background: linear-gradient(135deg, #f5f3ff 0%, #c4b5fd 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.page-sub {
    font-size: 0.88rem;
    color: #6d6a8a;
    margin: 0;
    font-weight: 400;
}

/* Section label */
.section-label {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #7c77a0;
    margin-bottom: 1.2rem;
    display: flex; align-items: center; gap: 0.6rem;
}
.section-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: linear-gradient(135deg, #a78bfa, #60a5fa);
    flex-shrink: 0;
}

/* KPI Grid */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 1rem;
    margin-bottom: 0.5rem;
}
.kpi-card {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 1.6rem 1.2rem;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s, background 0.2s;
    text-align: center;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(167,139,250,0.5), transparent);
}
.kpi-card.green::before { background: linear-gradient(90deg, transparent, rgba(52,211,153,0.6), transparent); }
.kpi-card.red::before   { background: linear-gradient(90deg, transparent, rgba(251,113,133,0.6), transparent); }
.kpi-card.amber::before { background: linear-gradient(90deg, transparent, rgba(251,191,36,0.6), transparent); }
.kpi-card:hover {
    background: rgba(255,255,255,0.07);
    border-color: rgba(167,139,250,0.25);
}
.kpi-num {
    font-size: 3.2rem;
    font-weight: 800;
    font-family: 'DM Mono', monospace;
    color: #c4b5fd;
    line-height: 1;
    letter-spacing: -0.02em;
}
.kpi-num.green { color: #34d399; }
.kpi-num.red   { color: #fb7185; }
.kpi-num.amber { color: #fbbf24; }
.kpi-lbl {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #7c77a0;
    margin-top: 8px;
}

/* Result card */
.result-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(167,139,250,0.2);
    border-radius: 16px;
    border-left: 4px solid #34d399;
    padding: 1.6rem;
    margin-top: 1rem;
    position: relative;
    overflow: hidden;
}
.result-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(52,211,153,0.4), transparent);
}
.result-card.fail {
    border-left-color: #fb7185;
}
.result-card.fail::before {
    background: linear-gradient(90deg, transparent, rgba(251,113,133,0.4), transparent);
}
.verdict-row {
    display: flex; align-items: center; gap: 12px;
    margin-bottom: 1.2rem;
}
.verdict-badge {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 5px 14px;
    border-radius: 20px;
    font-size: 0.75rem; font-weight: 700;
    letter-spacing: 0.08em;
    background: rgba(52,211,153,0.15);
    color: #34d399;
    border: 1px solid rgba(52,211,153,0.3);
}
.verdict-badge .material-icons-round { font-size: 15px; }
.verdict-badge.fail {
    background: rgba(251,113,133,0.15);
    color: #fb7185;
    border-color: rgba(251,113,133,0.3);
}
.verdict-score {
    font-size: 1.6rem;
    font-weight: 800;
    font-family: 'DM Mono', monospace;
    color: #34d399;
}
.verdict-score.fail { color: #fb7185; }
.verdict-label {
    font-size: 0.78rem;
    color: #5a5578;
    font-weight: 500;
}

/* Metric sub-boxes */
.metric-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
}
.metric-box {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px;
    padding: 1rem 1.1rem;
}
.metric-name {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #7c77a0;
    margin-bottom: 6px;
}
.metric-val {
    font-size: 1.5rem;
    font-weight: 800;
    font-family: 'DM Mono', monospace;
    color: #34d399;
}
.metric-val.warn { color: #fbbf24; }
.metric-val.fail { color: #fb7185; }
.bar-bg {
    background: rgba(255,255,255,0.07);
    border-radius: 4px; height: 4px;
    overflow: hidden; margin-top: 8px;
}
.bar-fg { height: 100%; border-radius: 4px; }
.bar-pass { background: #34d399; }
.bar-warn { background: #fbbf24; }
.bar-fail { background: #fb7185; }

/* RAGAS grid */
.ragas-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 1rem;
    margin-top: 1rem;
}
.ragas-box {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 1.4rem 1rem;
    text-align: center;
    transition: border-color 0.2s;
}
.ragas-box:hover { border-color: rgba(167,139,250,0.3); }
.ragas-val {
    font-size: 1.9rem;
    font-weight: 800;
    font-family: 'DM Mono', monospace;
    color: #a78bfa;
}
.ragas-lbl {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #5a5578;
    margin-top: 6px;
}

/* Chip row */
.chip-row { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 12px; }
.chip {
    background: rgba(167,139,250,0.1);
    border: 1px solid rgba(167,139,250,0.2);
    border-radius: 20px;
    padding: 3px 10px;
    font-size: 0.72rem;
    color: #9980fa;
    font-weight: 500;
}

/* Form card */
.form-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(167,139,250,0.15);
    border-radius: 16px;
    padding: 1.4rem;
    position: relative;
    overflow: hidden;
}
.form-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(167,139,250,0.4), transparent);
}

/* Divider custom */
.custom-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(167,139,250,0.2) 30%, rgba(167,139,250,0.2) 70%, transparent);
    margin: 2.2rem 0;
}
</style>
""", unsafe_allow_html=True)
# ── Explication ────────────────────────────────────────────────────────────────
col_exp1, col_exp2 = st.columns(2)
with col_exp1:
    st.markdown("""
    ### 🤖 Sans RAG — LLM seul
    Le modèle répond **uniquement depuis sa mémoire d'entraînement**.
    Il ne connaît pas HoodieWear, ses politiques, ses prix ou ses procédures.
    """)
with col_exp2:
    st.markdown("""
    ### 🎯 Avec RAG — Notre système
    Le modèle **consulte d'abord notre base de connaissances** avant de répondre.
    Les réponses sont précises, vérifiables et spécifiques à HoodieWear.
    """)

st.divider()

# ── Questions prédéfinies ──────────────────────────────────────────────────────
EXEMPLES = [
    "Quels sont les délais de livraison de HoodieWear ?",
    "Comment retourner un article chez HoodieWear ?",
    "Quels modes de paiement accepte HoodieWear ?",
    "Comment laver mon hoodie HoodieWear ?",
    "HoodieWear livre-t-il en Tunisie ?"
]

st.markdown("### 💬 Choisissez ou tapez une question")
col_q1, col_q2 = st.columns([2, 1])
with col_q1:
    question = st.text_input(
        "Question :",
        placeholder="Ex: Quels sont vos délais de livraison ?",
        label_visibility="collapsed"
    )
with col_q2:
    exemple_choisi = st.selectbox(
        "Ou choisir un exemple :",
        ["— Exemples —"] + EXEMPLES,
        label_visibility="collapsed"
    )

if exemple_choisi != "— Exemples —":
    question = exemple_choisi

if st.button("⚖️ Comparer", type="primary", use_container_width=False) and question:

    col1, col2 = st.columns(2)

    # ── Colonne SANS RAG ───────────────────────────────────────────────────────
    with col1:
        st.markdown("### 🤖 Sans RAG")
        st.caption("LLM seul — mémoire générale uniquement")
        with st.spinner("Génération sans RAG..."):
            try:
                t0 = time.time()
                response_sans_rag = call_groq_llm(
                    question=(
                        "Tu es un assistant e-commerce général. "
                        f"Réponds en français à cette question : {question}"
                    ),
                    context="Aucun contexte spécifique fourni.",
                    chat_history=[],
                    lang="french",
                    tone_instruction="Réponds depuis tes connaissances générales."
                )
                t1 = time.time()
                temps_sans_rag = round(t1 - t0, 2)

                st.info(response_sans_rag)
                st.caption(f"⏱️ Temps : {temps_sans_rag}s")

                # Problèmes
                st.markdown("**⚠️ Problèmes de cette réponse :**")
                st.markdown("- ❌ Ne connaît pas les politiques HoodieWear")
                st.markdown("- ❌ Réponse générique, pas personnalisée")
                st.markdown("- ❌ Peut inventer des informations (hallucination)")
                st.markdown("- ❌ Aucune source vérifiable")

            except Exception as e:
                st.error(f"Erreur : {e}")

    # ── Colonne AVEC RAG ───────────────────────────────────────────────────────
    with col2:
        st.markdown("### 🎯 Avec RAG")
        st.caption("Notre système — base de connaissances HoodieWear")
        with st.spinner("Recherche + Génération avec RAG..."):
            try:
                t0 = time.time()
                result = answer_question(question)
                t1 = time.time()
                temps_avec_rag = round(t1 - t0, 2)

                st.success(result["answer"])
                st.caption(f"⏱️ Temps : {temps_avec_rag}s")

                # Sources
                if result["sources"]:
                    with st.expander(f"📄 {len(result['sources'])} source(s) utilisée(s)"):
                        for src in result["sources"]:
                            st.markdown(
                                f"**Score : {src['score']}** — "
                                f"{src['content'][:200]}..."
                            )

                # Avantages
                st.markdown("**✅ Avantages de cette réponse :**")
                st.markdown("- ✅ Basée sur les vraies données HoodieWear")
                st.markdown(f"- ✅ {len(result['sources'])} source(s) documentée(s)")
                st.markdown("- ✅ Réponse vérifiable et traçable")
                st.markdown("- ✅ Mise à jour automatique avec la base")

            except Exception as e:
                st.error(f"Erreur : {e}")

    # ── Conclusion ─────────────────────────────────────────────────────────────
    st.divider()
    st.subheader("📊 Pourquoi le RAG est supérieur ?")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Précision", "RAG ✅", "Données réelles")
    c2.metric("Traçabilité", "RAG ✅", "Sources visibles")
    c3.metric("Fiabilité", "RAG ✅", "Pas d'hallucination")
    c4.metric("Mise à jour", "RAG ✅", "Base dynamique")

st.divider()
st.caption("⚖️ Cette page démontre l'apport scientifique du RAG — Référence : Lewis et al., 2020")