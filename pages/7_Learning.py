# pages/7_Learning.py
"""
Dashboard Continuous Learning RAG
==================================
Visualise en temps réel comment le système apprend
automatiquement depuis les feedbacks clients.
"""
import streamlit as st
import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.auth import require_agent_or_admin
from src.learning_pipeline import (
    auto_learn_from_feedback,
    batch_learn_from_all_feedbacks,
    learn_from_realtime_gaps,
    get_learning_stats,
    load_learning_log
)

# ── Auth ───────────────────────────────────────────────────────────────────────
user = require_agent_or_admin()

st.set_page_config(page_title="Learning RAG", page_icon="🧠", layout="wide")

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
}
[data-testid="stSidebar"] * { color: white !important; }
.metric-card {
    background: white; border-radius: 14px; padding: 20px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    text-align: center; border-top: 4px solid #e94560;
}
.metric-number { font-size: 2.2rem; font-weight: bold; color: #e94560; }
.metric-label  { font-size: 0.85rem; color: #888; margin-top: 4px; }
.learn-event-success {
    background: #f0fff4; border-left: 4px solid #1d9e75;
    border-radius: 8px; padding: 12px 16px; margin: 8px 0;
}
.learn-event-failed {
    background: #fff8e1; border-left: 4px solid #f0a500;
    border-radius: 8px; padding: 12px 16px; margin: 8px 0;
}
.improvement-badge {
    display: inline-block; padding: 3px 10px; border-radius: 12px;
    font-size: 0.8rem; font-weight: bold; color: white;
}
.hero {
    background: linear-gradient(135deg, #1a1a2e, #e94560);
    padding: 28px 36px; border-radius: 16px; color: white; margin-bottom: 24px;
}
</style>
""", unsafe_allow_html=True)
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
# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1 style="color:white;margin:0;">🧠 Continuous Learning RAG</h1>
    <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;">
        Le système apprend automatiquement depuis les feedbacks clients —
        sans intervention humaine.
    </p>
</div>
""", unsafe_allow_html=True)

# ── Stats globales ─────────────────────────────────────────────────────────────
stats = get_learning_stats()

c1, c2, c3, c4, c5 = st.columns(5)
metrics = [
    (stats["total_learned"],             "✅ Apprentissages réussis"),
    (f"{stats['success_rate']}%",        "🎯 Taux de succès"),
    (f"+{stats['avg_improvement']:.3f}", "📈 Amélioration moyenne"),
    (f"{stats['avg_score_before']:.2f} → {stats['avg_score_after']:.2f}", "🔢 Score RAG"),
    (f"{stats['avg_time_seconds']}s",    "⚡ Temps moyen"),
]
for col, (num, label) in zip([c1, c2, c3, c4, c5], metrics):
    with col:
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-number">{num}</div>'
            f'<div class="metric-label">{label}</div></div>',
            unsafe_allow_html=True
        )

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🚀 Déclencher apprentissage",
    "📊 Évolution des scores",
    "📋 Journal d'apprentissage",
    "🗺️ Topics appris"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Déclencher l'apprentissage
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### ⚡ Apprentissage automatique")

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### 🔴 Depuis les feedbacks négatifs")
        st.caption("Analyse tous les feedbacks 👎 et apprend les bonnes réponses.")

        # Compte les feedbacks négatifs
        fb_file = "data/feedback.json"
        neg_count = 0
        if os.path.exists(fb_file):
            try:
                with open(fb_file, "r", encoding="utf-8") as f:
                    fbs = json.loads(f.read().strip() or "[]")
                neg_count = len([f for f in fbs if f.get("rating") == "negative"])
            except Exception:
                pass

        st.metric("Feedbacks négatifs disponibles", neg_count)

        if st.button("🚀 Lancer batch learning", use_container_width=True,
                     type="primary", disabled=(neg_count == 0)):
            with st.spinner("🧠 Apprentissage en cours... (peut prendre quelques minutes)"):
                summary = batch_learn_from_all_feedbacks()

            st.success(f"✅ Terminé ! {summary['success']}/{summary['total']} réussis")
            st.metric("Taux de succès", f"{summary['success_rate']}%")

            if summary["details"]:
                with st.expander("📋 Détails"):
                    for r in summary["details"]:
                        color = "🟢" if r["status"] == "success" else "🟡"
                        st.caption(
                            f"{color} {r['question'][:60]}... | "
                            f"Score : {r['score_before']} → {r['score_after']} "
                            f"(Δ{r['improvement']:+.3f})"
                        )
            st.rerun()

    with col_b:
        st.markdown("#### 🟡 Depuis les gaps temps réel")
        st.caption("Traite les questions avec score RAG bas détectées automatiquement.")

        gaps_file = "data/potential_gaps_realtime.json"
        gap_count = 0
        if os.path.exists(gaps_file):
            try:
                with open(gaps_file, "r", encoding="utf-8") as f:
                    gaps = json.loads(f.read().strip() or "[]")
                gap_count = len([g for g in gaps if g.get("statut") == "non_traité"])
            except Exception:
                pass

        st.metric("Gaps non traités", gap_count)

        if st.button("🔍 Traiter les gaps", use_container_width=True,
                     disabled=(gap_count == 0)):
            with st.spinner("🧠 Traitement des gaps..."):
                result = learn_from_realtime_gaps()
            st.success(f"✅ {result['success']}/{result['total']} gaps traités")
            st.rerun()

    st.divider()

    # ── Test manuel ────────────────────────────────────────────────────────────
    st.markdown("#### 🧪 Test manuel — Apprentissage sur mesure")
    st.caption("Teste le pipeline sur une question spécifique.")

    with st.form("form_manual_learn"):
        q_test = st.text_input(
            "Question à apprendre",
            placeholder="Ex: Comment suivre ma commande ?"
        )
        bad_ans = st.text_area(
            "Réponse actuelle insuffisante",
            placeholder="Ex: Je n'ai pas trouvé d'information...",
            height=80
        )
        lang_sel = st.selectbox("Langue", ["fr", "en", "ar"])
        submit   = st.form_submit_button(
            "🧠 Déclencher l'apprentissage", type="primary", use_container_width=True
        )

    if submit and q_test:
        with st.spinner("🔄 Pipeline d'apprentissage en cours..."):
            result = auto_learn_from_feedback(q_test, bad_ans or "Aucune réponse.", lang_sel)

        # Affichage du résultat avec animation visuelle
        if result["status"] == "success":
            st.success(f"🎉 {result['message']}")
        else:
            st.warning(f"⚠️ {result['message']}")

        col1, col2, col3 = st.columns(3)
        with col1:
            delta = result["score_after"] - result["score_before"]
            st.metric("Score avant",  f"{result['score_before']:.3f}")
        with col2:
            st.metric("Score après",  f"{result['score_after']:.3f}",
                      delta=f"{delta:+.3f}")
        with col3:
            st.metric("Tentatives",   result["attempts"])
            st.metric("Durée",        f"{result['duration_seconds']}s")

        if result.get("learned_answer"):
            st.markdown("**📝 Réponse apprise :**")
            st.info(result["learned_answer"])

        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Évolution des scores
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### 📈 Évolution du score RAG dans le temps")

    evolution = stats.get("evolution_by_day", [])

    if not evolution:
        st.info("Aucune donnée d'évolution disponible. Lancez d'abord un apprentissage.")
    else:
        import pandas as pd

        df = pd.DataFrame(evolution)

        # Graphique d'amélioration
        st.markdown("#### Score RAG — Amélioration par jour")
        st.bar_chart(df.set_index("date")[["avg_improvement"]])

        st.markdown("#### Apprentissages réussis vs échoués")
        st.bar_chart(df.set_index("date")[["learned", "failed"]])

        st.markdown("#### Données brutes")
        st.dataframe(df, use_container_width=True)

    st.divider()

    # Comparaison avant/après
    st.markdown("### 🔢 Comparaison globale des scores RAG")
    log = load_learning_log()
    learned = [e for e in log if e.get("status") == "success" and e.get("score_after")]

    if learned:
        import pandas as pd
        df2 = pd.DataFrame([{
            "Question":      e["question"][:50] + "...",
            "Score avant":   e.get("score_before", 0),
            "Score après":   e.get("score_after", 0),
            "Amélioration":  e.get("improvement", 0),
            "Tentatives":    e.get("attempts", 1),
            "Topic":         e.get("topic", "?"),
        } for e in learned[-20:]])

        st.dataframe(
            df2.style.background_gradient(subset=["Amélioration"], cmap="Greens"),
            use_container_width=True
        )
    else:
        st.info("Aucun apprentissage réussi enregistré pour l'instant.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Journal d'apprentissage
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### 📋 Journal complet des apprentissages")

    log = load_learning_log()

    if not log:
        st.info("Aucun événement d'apprentissage enregistré.")
    else:
        # Filtre
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            status_filter = st.selectbox(
                "Filtrer par statut",
                ["Tous", "success", "failed"]
            )
        with filter_col2:
            topic_filter = st.selectbox(
                "Filtrer par topic",
                ["Tous"] + list(set(e.get("topic", "?") for e in log))
            )

        filtered = log.copy()
        if status_filter != "Tous":
            filtered = [e for e in filtered if e.get("status") == status_filter]
        if topic_filter != "Tous":
            filtered = [e for e in filtered if e.get("topic") == topic_filter]

        st.caption(f"{len(filtered)} événements affichés")

        # Affichage chronologique inversé
        for event in reversed(filtered[-30:]):
            is_ok  = event.get("status") == "success"
            css    = "learn-event-success" if is_ok else "learn-event-failed"
            icon   = "✅" if is_ok else "⚠️"
            imp    = event.get("improvement", 0)
            color  = "#1d9e75" if imp > 0 else "#f0a500"

            st.markdown(f"""
            <div class="{css}">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <b>{icon} {event.get('question','')[:70]}...</b>
                    <span style="color:#888;font-size:0.8rem;">{event.get('timestamp','')}</span>
                </div>
                <div style="margin-top:6px;font-size:0.85rem;color:#555;">
                    Topic : <b>{event.get('topic','?')}</b> |
                    Langue : <b>{event.get('lang','?')}</b> |
                    Tentatives : <b>{event.get('attempts','?')}</b> |
                    Durée : <b>{event.get('duration_seconds','?')}s</b>
                </div>
                <div style="margin-top:6px;">
                    <span class="improvement-badge" style="background:{color};">
                        Score : {event.get('score_before',0):.3f} → {event.get('score_after',0):.3f}
                        (Δ{imp:+.3f})
                    </span>
                </div>
                {f'<div style="margin-top:6px;font-size:0.82rem;color:#444;font-style:italic;">💬 {event.get("learned_answer","")[:120]}...</div>' if event.get("learned_answer") else ""}
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Distribution des topics
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### 🗺️ Topics appris par le système")

    topics = stats.get("topics_learned", {})

    if not topics:
        st.info("Aucun topic appris pour l'instant.")
    else:
        import pandas as pd

        df_topics = pd.DataFrame([
            {"Topic": k, "Apprentissages": v}
            for k, v in sorted(topics.items(), key=lambda x: x[1], reverse=True)
        ])

        col_chart, col_table = st.columns([2, 1])

        with col_chart:
            st.bar_chart(df_topics.set_index("Topic"))

        with col_table:
            st.dataframe(df_topics, use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("### 📚 Connaissances apprises")

        learned_file = "data/raw/faq_auto_learned.json"
        if os.path.exists(learned_file):
            try:
                with open(learned_file, "r", encoding="utf-8") as f:
                    learned_docs = json.loads(f.read().strip() or "[]")

                st.caption(f"{len(learned_docs)} documents auto-appris indexés dans ChromaDB")

                for doc in reversed(learned_docs[-10:]):
                    with st.expander(f"📄 {doc.get('question','')[:60]}..."):
                        st.markdown(f"**Réponse apprise :**")
                        st.info(doc.get("reponse", ""))
                        st.caption(
                            f"Tags : {', '.join(doc.get('tags', []))} | "
                            f"Date : {doc.get('date', '')} | "
                            f"Langue : {doc.get('langue', '')}"
                        )
            except Exception as e:
                st.error(f"Erreur lecture : {e}")
        else:
            st.info("Aucune connaissance apprise encore.")

# ── Footer ─────────────────────────────────────────────────────────────────────
st.divider()
st.markdown("""
<div style="text-align:center;color:#aaa;font-size:0.8rem;padding:10px;">
    🧠 Continuous Learning RAG — HoodieWear KMS v2.0 |
    Basé sur : Online Learning (Bottou, 1998) + RAG (Lewis et al., 2020)
</div>
""", unsafe_allow_html=True)