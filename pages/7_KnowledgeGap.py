# pages/7_KnowledgeGap.py — Version 3.1 — Bug fix session_state keys
"""
Page 7 — Knowledge Gap Detector & Auto-amélioration
====================================================
Fix v3.1 :
  - Séparation stricte des clés widget (btn_*) et données (data_*)
  - Suppression du conflit st.session_state key / widget key
"""

import streamlit as st
import sys
import os
import json
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.auth import require_agent_or_admin
user = require_agent_or_admin()

from src.knowledge_gap import (
    get_all_gaps,
    get_km_health_score,
    get_topic_distribution,
    get_predictive_gaps,
    generate_answer_for_gap,
    approve_and_index_entry,
    get_correction_rate,
    save_gaps,
    load_gaps,
    load_correction_log,
    GAP_FAQ_FILE,
    MAX_REGEN_ATTEMPTS
)

st.set_page_config(
    page_title="Knowledge Gap Detector",
    page_icon="🧠",
    layout="wide"
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.health-card {
    background: white; border-radius: 14px; padding: 18px 22px;
    text-align: center; box-shadow: 0 2px 12px rgba(0,0,0,0.07);
    border-top: 5px solid #e94560;
}
.health-number { font-size: 2.2rem; font-weight: 700; color: #e94560; }
.health-label  { font-size: 0.82rem; color: #666; margin-top: 4px; }
.correction-ok {
    background: #eafaf1; border: 1.5px solid #00cc66;
    border-radius: 10px; padding: 10px 14px; margin: 6px 0;
}
.correction-fail {
    background: #fef3cd; border: 1.5px solid #f39c12;
    border-radius: 10px; padding: 10px 14px; margin: 6px 0;
}
.predictif-card {
    background: #f0f4ff; border: 1.5px solid #3498db;
    border-radius: 10px; padding: 12px 16px; margin: 8px 0;
}
.seci-step {
    background: white; border-radius: 10px; padding: 14px;
    text-align: center; border: 1px solid #eee;
    box-shadow: 0 1px 6px rgba(0,0,0,0.05);
}
.seci-icon  { font-size: 1.8rem; }
.seci-title { font-weight: 600; margin: 6px 0 2px; font-size: 0.92rem; }
.seci-desc  { font-size: 0.78rem; color: #888; }
.badge-ouverts { background: #ffeaea; color: #c0392b;
                 padding: 3px 10px; border-radius: 12px;
                 font-size: 0.78rem; font-weight: 600; }
.badge-traites { background: #eafaf1; color: #1e8449;
                 padding: 3px 10px; border-radius: 12px;
                 font-size: 0.78rem; font-weight: 600; }
.delta-pos { color: #1e8449; font-weight: 700; }
.delta-neg { color: #c0392b; font-weight: 700; }
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
# ── Titre ──────────────────────────────────────────────────────────────────────
st.title("🧠 Knowledge Gap Detector v3.1")
st.caption(
    "Détection · Génération IA · Boucle de correction FERMÉE · "
    "Correction Rate · Module prédictif · Cycle SECI"
)
st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 0 : Cycle SECI
# ══════════════════════════════════════════════════════════════════════════════
with st.expander("📚 Cycle SECI — implémenté dans ce module", expanded=False):
    c1, c2, c3, c4 = st.columns(4)
    seci = [
        ("🔵", "Socialisation",   "Collecte feedbacks & conversations",     "Tacite → Tacite"),
        ("🟠", "Externalisation", "Détection auto des lacunes + scoring",   "Tacite → Explicite"),
        ("🟢", "Combinaison",     "LLM génère une nouvelle réponse FAQ",    "Explicite → Explicite"),
        ("🟣", "Internalisation", "Indexation ChromaDB + validation score", "Explicite → Système"),
    ]
    for col, (icon, title, desc, mode) in zip([c1, c2, c3, c4], seci):
        with col:
            st.markdown(f"""<div class="seci-step">
                <div class="seci-icon">{icon}</div>
                <div class="seci-title">{title}</div>
                <div class="seci-desc">{desc}</div>
                <div style="margin-top:6px;font-size:0.7rem;color:#bbb;">{mode}</div>
            </div>""", unsafe_allow_html=True)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 : KM Health Score
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("🏥 KM Health Score")
st.caption("Métrique multi-dimensionnelle basée sur le Correction Rate réel.")

health = get_km_health_score()
score  = health["score_global"]
color  = "#00cc44" if score >= 70 else "#ff8800" if score >= 45 else "#e94560"

col_score, col_dims = st.columns([1, 3])

with col_score:
    st.markdown(f"""
    <div style="text-align:center;padding:28px 20px;background:white;
                border-radius:16px;box-shadow:0 2px 12px rgba(0,0,0,0.08);">
        <div style="font-size:3.5rem;font-weight:700;color:{color};">{score:.0f}</div>
        <div style="font-size:0.9rem;color:#666;margin-top:4px;">/ 100</div>
        <div style="font-size:0.82rem;color:#888;margin-top:8px;">Score KM Global</div>
        <div style="margin-top:10px;">
            <span class="{'badge-traites' if score >= 60 else 'badge-ouverts'}">
                {'🟢 Bonne santé' if score >= 70 else '🟡 À améliorer' if score >= 45 else '🔴 Critique'}
            </span>
        </div>
    </div>""", unsafe_allow_html=True)

with col_dims:
    dims = [
        ("🎯 Satisfaction client",          health["satisfaction"], "#e94560"),
        ("📚 Couverture des sujets",        health["couverture"],   "#3498db"),
        ("🔄 Fraîcheur (Correction Rate)",  health["fraicheur"],    "#2ecc71"),
        ("⚡ Réactivité KM",               health["reactivite"],   "#f39c12"),
    ]
    for label, val, clr in dims:
        col_l, col_b = st.columns([1, 3])
        with col_l:
            st.markdown(f"<small style='color:#555'>{label}</small>",
                        unsafe_allow_html=True)
        with col_b:
            st.progress(min(1.0, val / 100), text=f"{val:.0f}%")

st.markdown("")
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Lacunes ouvertes",  health["nb_gaps_ouverts"])
m2.metric("Lacunes traitées",  health["nb_gaps_traites"])
m3.metric("Docs auto-générés", health["nb_auto_docs"])
m4.metric("Total feedbacks",   health["total_feedbacks"])
m5.metric("🎯 Correction Rate",
          f"{health['correction_rate']:.0f}%",
          delta=f"{health['nb_corrected']}/{health['nb_attempted']} corrigées")
m6.metric("📈 Delta score moyen",
          f"{health['avg_delta_score']:+.3f}")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 : Lacunes prédictives
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("🔮 Lacunes prédictives — Anticipation à 7 jours")
st.caption(
    "Sujets avec fréquence croissante ET score RAG bas → lacunes émergentes "
    "avant d'avoir des feedbacks négatifs."
)

col_pred, col_info_pred = st.columns([1, 3])
with col_pred:
    if st.button("🔮 Analyser les tendances", use_container_width=True):
        with st.spinner("Analyse prédictive..."):
            try:
                predictive_gaps = get_predictive_gaps(window_days=7)
                st.session_state["predictive_gaps"] = predictive_gaps
                st.success(f"✅ {len(predictive_gaps)} tendance(s) détectée(s)")
            except Exception as e:
                st.error(f"Erreur : {e}")
with col_info_pred:
    st.caption("Analyse les 7 derniers jours de conversations pour identifier "
               "les sujets émergents avant qu'ils ne génèrent des plaintes.")

if "predictive_gaps" in st.session_state:
    pred_gaps = st.session_state["predictive_gaps"]
    if not pred_gaps:
        st.success("✅ Aucune tendance préoccupante détectée sur 7 jours.")
    else:
        for pg in pred_gaps:
            score_color = "#e94560" if pg["score_rag_moyen"] < 0.3 else "#f39c12"
            st.markdown(f"""<div class="predictif-card">
                <b>📌 Sujet émergent : {pg['sujet'].upper()}</b>
                &nbsp;&nbsp;
                <span style="background:#3498db;color:white;padding:2px 8px;
                      border-radius:8px;font-size:0.78rem;">
                    {pg['frequence_7j']} questions / 7j
                </span>
                &nbsp;
                <span style="background:{score_color};color:white;padding:2px 8px;
                      border-radius:8px;font-size:0.78rem;">
                    Score RAG moyen : {pg['score_rag_moyen']}
                </span>
                <br><small style="color:#555;margin-top:4px;display:block;">
                Exemples : {' | '.join(pg.get('questions_exemple', [])[:2])}
                </small>
            </div>""", unsafe_allow_html=True)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 : Distribution des sujets
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("📊 Distribution des sujets")

topics = get_topic_distribution()
if any(v > 0 for v in topics.values()):
    df_topics = pd.DataFrame([
        {"Sujet": k.capitalize(), "Fréquence": v}
        for k, v in topics.items() if v > 0
    ]).sort_values("Fréquence", ascending=False)
    st.bar_chart(df_topics.set_index("Sujet"))
    top_sujet = df_topics.iloc[0]["Sujet"] if len(df_topics) > 0 else "N/A"
    st.info(f"💡 **Insight KM** : Le sujet **{top_sujet}** est le plus demandé.")
else:
    st.info("Pas encore assez de données.")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 : Détection et traitement des lacunes
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("🔍 Lacunes détectées")

col_detect, col_info = st.columns([1, 3])
with col_detect:
    if st.button("🔍 Analyser les lacunes", type="primary", use_container_width=True):
        with st.spinner("Analyse en cours..."):
            gaps = get_all_gaps()
            save_gaps(gaps)
            st.success(f"✅ {len(gaps)} lacune(s) détectée(s) !")
            st.rerun()
with col_info:
    st.caption("Analyse feedbacks négatifs + conversations avec score RAG bas. "
               "Déduplication sémantique via embeddings.")

gaps = load_gaps()

if not gaps:
    st.info("Aucune lacune détectée. Cliquez sur 'Analyser les lacunes'.")
else:
    ouvertes = [g for g in gaps if g.get("statut") != "traité"]
    traitees = [g for g in gaps if g.get("statut") == "traité"]

    tab1, tab2, tab3 = st.tabs([
        f"🔴 Lacunes ouvertes ({len(ouvertes)})",
        f"✅ Lacunes traitées ({len(traitees)})",
        "📊 Log des corrections"
    ])

    # ── Tab 1 : Lacunes ouvertes ───────────────────────────────────────────
    with tab1:
        if not ouvertes:
            st.success("🎉 Toutes les lacunes ont été traitées !")
        else:
            for gap in ouvertes:
                gap_id     = gap["id"]
                # ✅ CLÉ DONNÉES séparée de la clé widget
                data_key   = f"data_{gap_id}"
                lang_flag  = {"fr": "🇫🇷", "en": "🇬🇧", "ar": "🇹🇳"}.get(
                    gap.get("langue", "fr"), "🌍")
                freq       = gap.get("occurrences", 1)
                type_badge = (
                    "🔴 Feedback négatif"
                    if gap.get("type") == "feedback_negatif"
                    else f"🟡 Score RAG bas ({gap.get('score_rag', '?')})"
                )
                score_avant = gap.get("score_rag_avant")
                score_label = f" | Score: {score_avant}" if score_avant is not None else ""

                with st.expander(
                    f"{lang_flag} {gap['question'][:70]}... "
                    f"| {type_badge} | Occ: {freq}{score_label}"
                ):
                    st.markdown(f"**Question complète :** {gap['question']}")

                    if gap.get("reponse_actuelle"):
                        st.markdown("**Réponse actuelle insuffisante :**")
                        st.caption(gap["reponse_actuelle"])

                    # ── Bouton Générer ─────────────────────────────────────
                    # ✅ Clé widget = btn_gen_{gap_id}, sans collision avec data_key
                    if st.button("🤖 Générer une réponse IA",
                                 key=f"btn_gen_{gap_id}",
                                 type="primary",
                                 use_container_width=True):
                        with st.spinner("Génération en cours..."):
                            gap["score_rag_avant"] = gap.get("score_rag", 0.0) or 0.0
                            new_entry = generate_answer_for_gap(gap, attempt=1)
                            if new_entry:
                                # ✅ Stocke dans data_key, PAS dans la clé widget
                                st.session_state[data_key] = new_entry
                                st.success("✅ Réponse générée ! Vérifiez ci-dessous.")
                            else:
                                st.error("Erreur de génération. Réessayez.")

                    # ── Affiche la réponse générée ─────────────────────────
                    if data_key in st.session_state and \
                       isinstance(st.session_state[data_key], dict):

                        entry   = st.session_state[data_key]
                        attempt = entry.get("attempt", 1)

                        if attempt > 1:
                            st.warning(
                                f"⚠️ Tentative {attempt}/{MAX_REGEN_ATTEMPTS} "
                                f"(la correction précédente n'a pas atteint le seuil)"
                            )

                        st.markdown("---")
                        st.markdown("**📝 Réponse générée par IA :**")

                        # ✅ Clé widget text_area = edit_{gap_id}_{attempt}
                        new_answer = st.text_area(
                            "Modifiez si nécessaire :",
                            value=entry["reponse"],
                            key=f"edit_{gap_id}_{attempt}",
                            height=100
                        )
                        # Met à jour la réponse en mémoire si modifiée
                        st.session_state[data_key]["reponse"] = new_answer

                        col_val, col_rej = st.columns(2)

                        with col_val:
                            # ✅ Clé widget = btn_val_{gap_id}_{attempt}
                            if st.button("✅ Valider & Indexer",
                                         key=f"btn_val_{gap_id}_{attempt}",
                                         type="primary",
                                         use_container_width=True):
                                with st.spinner("Indexation + validation score..."):
                                    # Récupère la version potentiellement modifiée
                                    entry_to_save = st.session_state[data_key]
                                    result = approve_and_index_entry(entry_to_save)

                                    if result["success"]:
                                        val       = result["validation"]
                                        delta_str = f"{val['delta']:+.3f}"

                                        if val["corrected"]:
                                            st.success(
                                                f"🎉 Lacune corrigée ! "
                                                f"Score : {val['score_before']} "
                                                f"→ {val['score_after']} (Δ {delta_str})"
                                            )
                                            st.balloons()
                                        else:
                                            st.warning(
                                                f"⚠️ Indexé mais score insuffisant. "
                                                f"Score : {val['score_before']} "
                                                f"→ {val['score_after']} "
                                                f"(Δ {delta_str}) | Seuil : 0.55"
                                            )
                                            # Re-génération automatique si nécessaire
                                            if result.get("needs_regen"):
                                                st.info("💡 Re-génération avec prompt renforcé...")
                                                gap["score_rag_avant"] = val["score_after"]
                                                regen = generate_answer_for_gap(gap, attempt=2)
                                                if regen:
                                                    # ✅ Stocke dans data_key (pas de widget conflict)
                                                    st.session_state[data_key] = regen
                                                    st.info("🔄 Nouvelle version. Validez-la.")
                                                    st.rerun()

                                        # Nettoyage après validation
                                        del st.session_state[data_key]
                                        st.rerun()
                                    else:
                                        st.error("Erreur lors de l'indexation.")

                        with col_rej:
                            # ✅ Clé widget = btn_rej_{gap_id}_{attempt}
                            if st.button("❌ Rejeter",
                                         key=f"btn_rej_{gap_id}_{attempt}",
                                         use_container_width=True):
                                del st.session_state[data_key]
                                st.rerun()

    # ── Tab 2 : Lacunes traitées ───────────────────────────────────────────
    with tab2:
        if not traitees:
            st.info("Aucune lacune traitée pour l'instant.")
        else:
            for gap in traitees:
                score_avant = gap.get("score_rag_avant")
                score_apres = gap.get("score_rag_apres")
                correction  = gap.get("correction_ok")
                delta       = gap.get("delta_score")

                if score_avant is not None and score_apres is not None:
                    delta_str  = f"{delta:+.3f}" if delta is not None else "N/A"
                    status_icon = "✅" if correction else "⚠️"
                    score_info  = (
                        f" | Score: {score_avant} → {score_apres} "
                        f"(Δ {delta_str}) {status_icon}"
                    )
                else:
                    score_info = ""

                st.markdown(
                    f"✅ **{gap['question'][:80]}...**"
                    f"<small style='color:#888'> — Traité le "
                    f"{gap.get('date_resolution', 'N/A')}{score_info}</small>",
                    unsafe_allow_html=True
                )

    # ── Tab 3 : Log des corrections ────────────────────────────────────────
    with tab3:
        log = load_correction_log()
        if not log:
            st.info("Aucune correction loggée pour l'instant.")
        else:
            correction_info = get_correction_rate()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Corrections tentées",  correction_info["nb_attempted"])
            c2.metric("Corrections réussies", correction_info["nb_corrected"])
            c3.metric("Correction Rate",
                      f"{correction_info['correction_rate']:.0f}%")
            avg_delta_val = correction_info.get("avg_delta_score",
                correction_info.get("avg_delta", 0.0))
            c4.metric("Delta moyen", f"{avg_delta_val:+.3f}")

            st.markdown("---")
            df_log = pd.DataFrame(log)
            df_log["corrected_label"] = df_log["corrected"].map(
                {True: "✅ Corrigé", False: "⚠️ Insuffisant"}
            )
            st.dataframe(
                df_log[["date", "question", "score_before", "score_after",
                         "delta", "corrected_label", "attempt"]].rename(columns={
                    "date":            "Date",
                    "question":        "Question",
                    "score_before":    "Score avant",
                    "score_after":     "Score après",
                    "delta":           "Delta",
                    "corrected_label": "Statut",
                    "attempt":         "Tentative"
                }),
                use_container_width=True
            )

            csv = df_log.to_csv(index=False, encoding="utf-8")
            st.download_button(
                "⬇️ Exporter le log des corrections (CSV)",
                csv,
                "correction_log.csv",
                "text/csv"
            )

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 : Base auto-enrichie
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("📚 Base de connaissances auto-enrichie")
st.caption("Entrées générées par IA, validées et indexées automatiquement.")

auto_docs = []
if os.path.exists(GAP_FAQ_FILE):
    try:
        with open(GAP_FAQ_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            auto_docs = json.loads(content) if content else []
    except Exception:
        pass

if not auto_docs:
    st.info("Aucune entrée auto-générée. Traitez une lacune ci-dessus.")
else:
    st.success(f"✅ **{len(auto_docs)} entrée(s)** ajoutées automatiquement à la base.")
    corrected_count = sum(
        1 for d in auto_docs if d.get("score_rag_apres", 0) >= 0.55
    )
    st.caption(f"Dont {corrected_count} avec score RAG validé ≥ 0.55")

    for doc in auto_docs:
        score_avant = doc.get("score_rag_avant")
        score_apres = doc.get("score_rag_apres")
        if score_avant is not None and score_apres is not None:
            score_str = f"Score : {score_avant} → {score_apres}"
            ok_icon   = "✅" if score_apres >= 0.55 else "⚠️"
        else:
            score_str = "Score non mesuré"
            ok_icon   = "❓"

        with st.expander(
            f"{ok_icon} {doc.get('question', 'N/A')[:70]}... "
            f"| {doc.get('date_validation', doc.get('date_creation', 'N/A'))}"
        ):
            st.markdown(f"**Question :** {doc['question']}")
            st.markdown(f"**Réponse :** {doc['reponse']}")
            st.markdown(f"**Tags :** {', '.join(doc.get('tags', []))}")
            if score_avant is not None:
                delta = round((score_apres or 0) - score_avant, 3)
                st.caption(
                    f"{score_str} | Δ {delta:+.3f} | "
                    f"Langue : {doc.get('langue', 'fr')} | "
                    f"Tentative n°{doc.get('attempt', 1)}"
                )

st.divider()


