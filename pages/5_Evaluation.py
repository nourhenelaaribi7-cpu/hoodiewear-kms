
import streamlit as st
import sys
import os
import json
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="Évaluation LLM", page_icon="⚖️", layout="wide")

from src.auth import require_agent_or_admin
user = require_agent_or_admin()

# ══════════════════════════════════════════════════════════════════════════════
# CSS — Thème Dark Purple identique à la page Stats
# ══════════════════════════════════════════════════════════════════════════════
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
body {
    color: #e8e6f0;
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

/* ── Inputs & Textareas FIX ── */
.stTextArea textarea,
.stTextInput input {
    background: rgba(30, 27, 75, 0.6) !important; /* fond sombre */
    border: 1px solid rgba(167, 139, 250, 0.25) !important;
    border-radius: 10px !important;
    color: #f5f3ff !important; /* texte bien visible */
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.92rem !important;
    line-height: 1.6 !important;
    caret-color: #a78bfa !important;
}

/* Placeholder visible */
.stTextArea textarea::placeholder,
.stTextInput input::placeholder {
    color: #7c77a0 !important;
}

/* Focus */
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
[data-testid="stAlert"] {
    background: rgba(30, 58, 138, 0.25) !important; /* bleu foncé lisible */
    border: 1px solid rgba(96,165,250,0.4) !important;
}

[data-testid="stAlert"] p {
    color: #e0e7ff !important; /* texte clair */
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

# ── Fichiers ───────────────────────────────────────────────────────────────────
JUDGE_LOG     = "data/judge_log.json"
RAGAS_SCORES  = "data/ragas_scores.json"
RAGAS_HISTORY = "data/ragas_scores_history.json"


# ── Helpers ────────────────────────────────────────────────────────────────────
def safe_float(val, default=0.0):
    if isinstance(val, list):
        val = val[0] if val else default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def score_cls(s):
    if s >= 0.7: return "pass", "bar-pass"
    if s >= 0.5: return "warn", "bar-warn"
    return "fail", "bar-fail"


def section_label(text):
    st.markdown(f"""
    <div class="section-label">
        <span class="section-dot"></span>
        {text}
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="page-header">
    <div class="eyebrow">Tableau de bord</div>
    <div class="page-title">Évaluation LLM</div>
    <p class="page-sub">LLM-as-a-Judge · Faithfulness · Relevancy · Context Precision · Completeness</p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — STATISTIQUES EN TEMPS RÉEL
# ══════════════════════════════════════════════════════════════════════════════
section_label("Statistiques judge en temps réel")

try:
    from src.judge_llm import get_judge
    stats = get_judge().get_stats()
except Exception:
    stats = {}

total  = stats.get("total", 0)
passed = stats.get("passed", 0)
failed = stats.get("failed", 0)
pr     = safe_float(stats.get("pass_rate", 0))
sc     = safe_float(stats.get("avg_score", 0))

pr_num_cls = "green" if pr >= 70 else "amber" if pr >= 50 else "red"
pr_card_cls = pr_num_cls

st.markdown(f"""
<div class="kpi-grid">
    <div class="kpi-card">
        <div class="kpi-num">{total}</div>
        <div class="kpi-lbl">Évaluations totales</div>
    </div>
    <div class="kpi-card green">
        <div class="kpi-num green">{passed}</div>
        <div class="kpi-lbl">Passed</div>
    </div>
    <div class="kpi-card red">
        <div class="kpi-num red">{failed}</div>
        <div class="kpi-lbl">Failed</div>
    </div>
    <div class="kpi-card {pr_card_cls}">
        <div class="kpi-num {pr_num_cls}">{pr:.0f}%</div>
        <div class="kpi-lbl">Taux de succès</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-num">{sc:.3f}</div>
        <div class="kpi-lbl">Score moyen</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — ÉVALUATION MANUELLE
# ══════════════════════════════════════════════════════════════════════════════
section_label("Évaluer une réponse manuellement")

st.markdown('<div class="form-card">', unsafe_allow_html=True)

with st.form("form_judge_manual"):
    col_q, col_a = st.columns(2)
    with col_q:
        test_q = st.text_area(
            "Question client",
            value="Quels sont les délais de livraison en Tunisie ?",
            height=100,
        )
    with col_a:
        test_a = st.text_area(
            "Réponse du chatbot",
            value="La livraison en Tunisie prend entre 3 et 5 jours ouvrés.",
            height=100,
        )
    test_ctx = st.text_area(
        "Contexte RAG utilisé (optionnel)",
        value="Livraison Tunisie : 3-5 jours | Europe : 5-10 jours | International : 10-15 jours",
        height=60,
    )
    submitted = st.form_submit_button(
        "Lancer l'évaluation", type="primary", use_container_width=True
    )

st.markdown('</div>', unsafe_allow_html=True)

if submitted and test_q and test_a:
    with st.spinner("Évaluation en cours..."):
        try:
            from src.judge_llm import get_judge
            result = get_judge().evaluate(
                question=test_q,
                answer=test_a,
                context=test_ctx,
                sources=[],
                save_log=True,
            )

            verdict      = result.get("verdict", "fail")
            global_score = safe_float(result.get("global_score", 0))
            faithfulness = safe_float(result.get("faithfulness", 0))
            relevancy    = safe_float(result.get("relevancy", 0))
            context_prec = safe_float(result.get("context_precision", 0))
            completeness = safe_float(result.get("completeness", 0))

            is_pass   = verdict == "pass"
            card_cls  = "" if is_pass else "fail"
            badge_cls = "" if is_pass else "fail"
            icon      = "check_circle" if is_pass else "cancel"
            score_cls_v = "" if is_pass else "fail"

            metrics_html = ""
            for name, val in [
                ("Faithfulness",      faithfulness),
                ("Relevancy",         relevancy),
                ("Context Precision", context_prec),
                ("Completeness",      completeness),
            ]:
                vc, bc = score_cls(val)
                pct = int(val * 100)
                metrics_html += f"""
                <div class="metric-box">
                    <div class="metric-name">{name}</div>
                    <div class="metric-val {vc}">{val:.3f}</div>
                    <div class="bar-bg">
                        <div class="bar-fg {bc}" style="width:{pct}%"></div>
                    </div>
                </div>"""

            st.markdown(f"""
            <div class="result-card {card_cls}">
                <div class="verdict-row">
                    <div class="verdict-badge {badge_cls}">
                        <span class="material-icons-round">{icon}</span>
                        {verdict.upper()}
                    </div>
                    <span class="verdict-score {score_cls_v}">{global_score:.3f}</span>
                    <span class="verdict-label">score global</span>
                </div>
                <div class="metric-row">{metrics_html}</div>
            </div>
            """, unsafe_allow_html=True)

            if result.get("issues"):
                st.warning("Problèmes détectés : " + " · ".join(result["issues"]))

        except Exception as e:
            st.error(f"Erreur évaluation : {e}")
            st.info("Vérifiez que src/judge_llm.py est présent et que GROQ_API_KEY est configurée.")

st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — VALIDATION RAGAS
# ══════════════════════════════════════════════════════════════════════════════
section_label("Validation RAGAS automatique — 20 questions")

col_run, col_info = st.columns([1, 2])
with col_run:
    if st.button("Lancer la validation complète", type="primary", use_container_width=True):
        with st.spinner("Évaluation RAGAS sur 20 questions... (2-3 min)"):
            try:
                from src.validator import run_full_validation_pipeline
                result_v = run_full_validation_pipeline()
                st.session_state["last_ragas"] = result_v
                st.success("Validation terminée avec succès.")
            except Exception as e:
                st.error(f"Erreur : {e}")
                st.info("Vérifiez que ChromaDB est indexé et que GROQ_API_KEY est configurée.")

with col_info:
    st.info(
        "Le pipeline teste 20 questions couvrant tous les topics "
        "(livraison, retour, paiement, taille, entretien, compte). "
        "Il détecte automatiquement les régressions supérieures à 5%."
    )

# Affichage RAGAS
ragas_scores = None
if os.path.exists(RAGAS_SCORES):
    try:
        with open(RAGAS_SCORES, "r", encoding="utf-8") as f:
            ragas_scores = json.loads(f.read().strip() or "{}")
    except Exception:
        pass

if ragas_scores:
    boxes_html = ""
    for label, key in [
        ("Faithfulness",      "faithfulness"),
        ("Answer Relevancy",  "answer_relevancy"),
        ("Context Precision", "context_precision"),
        ("Context Recall",    "context_recall"),
        ("RAGAS Score",       "ragas_score"),
    ]:
        val   = safe_float(ragas_scores.get(key, 0))
        color = "#34d399" if val >= 0.7 else "#fbbf24" if val >= 0.5 else "#fb7185"
        boxes_html += f"""
        <div class="ragas-box">
            <div class="ragas-val" style="color:{color}">{val:.3f}</div>
            <div class="ragas-lbl">{label}</div>
        </div>"""

    ts = ragas_scores.get("timestamp", "—")
    nb = ragas_scores.get("nb_questions", "—")
    nf = ragas_scores.get("nb_failed", 0)

    st.markdown(f"""
    <div class="ragas-grid">{boxes_html}</div>
    <div class="chip-row">
        <div class="chip">Évalué le {ts}</div>
        <div class="chip">{nb} questions</div>
        <div class="chip">{nf} échec(s)</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — ÉVOLUTION DES SCORES RAGAS
# ══════════════════════════════════════════════════════════════════════════════
section_label("Évolution des scores RAGAS")

history = []
if os.path.exists(RAGAS_HISTORY):
    try:
        with open(RAGAS_HISTORY, "r", encoding="utf-8") as f:
            history = json.loads(f.read().strip() or "[]")
    except Exception:
        pass

if len(history) >= 2:
    import pandas as pd
    df = pd.DataFrame(history[-30:])
    for col_name in ["faithfulness", "answer_relevancy", "context_precision", "ragas_score"]:
        if col_name in df.columns:
            df[col_name] = df[col_name].apply(lambda x: safe_float(x))
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    cols_to_plot = [c for c in
        ["faithfulness", "answer_relevancy", "context_precision", "ragas_score"]
        if c in df.columns]
    if cols_to_plot:
        st.line_chart(df.set_index("date")[cols_to_plot], color=["#a78bfa", "#60a5fa", "#34d399", "#fbbf24"])
elif history:
    st.info("Lancez au moins 2 évaluations pour voir l'évolution.")
else:
    st.info("Aucun historique RAGAS. Lancez la validation ci-dessus.")

st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — LOG DES ÉVALUATIONS
# ══════════════════════════════════════════════════════════════════════════════
section_label("Dernières évaluations Judge")

judge_log = []
if os.path.exists(JUDGE_LOG):
    try:
        with open(JUDGE_LOG, "r", encoding="utf-8") as f:
            judge_log = json.loads(f.read().strip() or "[]")
    except Exception:
        pass

if judge_log:
    for entry in reversed(judge_log[-10:]):
        verdict  = entry.get("verdict", "?")
        score    = safe_float(entry.get("global_score", 0))
        question = entry.get("question", "")[:65]
        ts       = entry.get("timestamp", "")[:16]
        is_pass  = verdict == "pass"
        icon_lbl = "✓" if is_pass else "✗"
        score_color = "#34d399" if is_pass else "#fb7185"

        with st.expander(f"{icon_lbl}  [{ts}]  {question}…   —   {score:.3f}"):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Faithfulness",      f"{safe_float(entry.get('faithfulness', 0)):.3f}")
            c2.metric("Relevancy",         f"{safe_float(entry.get('relevancy', 0)):.3f}")
            c3.metric("Context Precision", f"{safe_float(entry.get('context_precision', 0)):.3f}")
            c4.metric("Completeness",      f"{safe_float(entry.get('completeness', 0)):.3f}")
            if entry.get("issues"):
                st.warning("Problèmes : " + " · ".join(entry["issues"]))
else:
    st.info("Aucune évaluation enregistrée. Lancez un test manuel ci-dessus.")

st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — TEST PIPELINE LANGGRAPH
# ══════════════════════════════════════════════════════════════════════════════
section_label("Test pipeline LangGraph")

with st.form("form_graph_test"):
    test_question = st.text_input(
        "Question test",
        value="Comment retourner un article chez HoodieWear ?",
    )
    use_graph = st.toggle("Utiliser le pipeline LangGraph", value=True)
    submit_g  = st.form_submit_button("Tester", type="primary")

if submit_g and test_question:
    with st.spinner("Pipeline en cours..."):
        try:
            if use_graph:
                from src.rag_pipeline import answer_question_graph
                result_g = answer_question_graph(test_question)
            else:
                from src.rag_chain import answer_question
                result_g = answer_question(test_question)

            st.success("Réponse générée avec succès.")
            st.markdown(f"**Réponse :** {result_g['answer']}")

            col_g1, col_g2, col_g3 = st.columns(3)
            col_g1.metric("Langue",    result_g.get("language", "—"))
            col_g2.metric("Score RAG", f"{safe_float(result_g.get('avg_score', 0)):.3f}")
            col_g3.metric("Cache",     "Oui" if result_g.get("from_cache") else "Non")

            if use_graph and result_g.get("judge"):
                j = result_g["judge"]
                st.markdown("**Judge inline :**")
                jc1, jc2, jc3 = st.columns(3)
                jc1.metric("Score",       f"{safe_float(j.get('score', 0)):.3f}")
                jc2.metric("Verdict",      j.get("verdict", "—"))
                jc3.metric("Faithfulness", f"{safe_float(j.get('faithfulness', 0)):.3f}")

            if result_g.get("suggestions"):
                st.markdown("**Suggestions :** " + " · ".join(result_g["suggestions"]))

        except ImportError as e:
            st.warning(f"Module manquant : {e}")
            st.info("Copiez rag_pipeline.py et judge_llm.py dans votre dossier src/")
        except Exception as e:
            st.error(f"Erreur : {e}")