# pages/4_Analytics.py 
"""
Dashboard KM Health Score
"""
import streamlit as st
import sys
import os
import json
import math
from datetime import datetime, timedelta
from collections import Counter

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="KM Analytics", page_icon="📊", layout="wide")

from src.auth import require_agent_or_admin
user = require_agent_or_admin()

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* ── App background ── */
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #141428 50%, #0f0c29 100%);
        color: #e8e6f0;
        min-height: 100vh;
    }
    .stApp::before {
        content: '';
        position: fixed;
        inset: 0;
        background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E");
        pointer-events: none;
        z-index: 0;
    }

    .block-container {
        padding-top: 2rem;
        max-width: 1300px;
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

    /* ── Page Header ── */
    .page-header {
        padding: 2.5rem 0 2rem 0;
        margin-bottom: 2.5rem;
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
    .page-header-eyebrow {
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: #a78bfa;
        margin-bottom: 0.6rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .page-header-eyebrow::before {
        content: '';
        display: inline-block;
        width: 18px; height: 2px;
        background: #a78bfa; border-radius: 1px;
    }
    .page-header h1 {
        font-size: 3.4rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        margin: 0 0 0.4rem 0;
        line-height: 1;
        background: linear-gradient(135deg, #f5f3ff 0%, #c4b5fd 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .page-header p { font-size: 0.9rem; color: #6d6a8a; margin: 0; font-weight: 400; }

    /* ── KM Score Ring ── */
    .km-score-ring {
        text-align: center;
        padding: 2.5rem 1.5rem;
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 20px;
        position: relative;
        overflow: hidden;
        height: 100%;
    }
    .km-score-ring::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: linear-gradient(90deg, #a78bfa, #60a5fa, #34d399);
        border-radius: 2px 2px 0 0;
    }
    .km-score-glow {
        position: absolute;
        width: 150px; height: 150px;
        border-radius: 50%;
        top: -30px; right: -30px;
        filter: blur(50px);
        opacity: 0.08;
        background: #a78bfa;
    }
    .km-score-label {
        font-size: 0.62rem;
        font-weight: 700;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: #7c77a0;
        margin-bottom: 0.5rem;
    }
    .km-score-num {
        font-size: 5.5rem;
        font-weight: 800;
        font-family: 'DM Mono', monospace;
        line-height: 1;
        margin: 0.3rem 0 0.2rem;
        letter-spacing: -0.04em;
    }
    .km-score-denom {
        font-size: 0.85rem;
        color: #5a5578;
        font-family: 'DM Mono', monospace;
        margin-bottom: 0.8rem;
    }
    .km-score-badge {
        display: inline-block;
        padding: 0.3rem 1rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        margin-bottom: 1rem;
    }
    .km-score-breakdown {
        font-family: 'DM Mono', monospace;
        font-size: 0.75rem;
        color: #5a5578;
        line-height: 2;
    }
    .km-score-breakdown span { color: #9d98c0; }

    /* ── SECI Cards ── */
    .seci-card {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 16px;
        padding: 1.6rem 1.4rem;
        height: 100%;
        position: relative;
        overflow: hidden;
        transition: background 0.2s, border-color 0.2s;
    }
    .seci-card:hover {
        background: rgba(255,255,255,0.05);
    }
    .seci-card-top {
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        border-radius: 2px 2px 0 0;
    }
    .seci-card-glow {
        position: absolute;
        width: 80px; height: 80px;
        border-radius: 50%;
        top: -20px; right: -20px;
        filter: blur(30px);
        opacity: 0.1;
    }
    .seci-letter {
        font-size: 3rem;
        font-weight: 800;
        font-family: 'DM Mono', monospace;
        line-height: 1;
        margin-bottom: 0.3rem;
    }
    .seci-title { font-size: 0.95rem; font-weight: 700; color: #e8e6f0; }
    .seci-subtitle { font-size: 0.72rem; color: #6d6a8a; margin-bottom: 1rem; font-weight: 400; }
    .seci-score-num {
        font-size: 2.2rem;
        font-weight: 800;
        font-family: 'DM Mono', monospace;
        line-height: 1;
        margin: 0.5rem 0 0.3rem;
    }
    .seci-bar-bg {
        background: rgba(255,255,255,0.07);
        border-radius: 4px;
        height: 6px;
        overflow: hidden;
        margin-bottom: 1rem;
    }
    .seci-bar-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.6s ease;
    }

    /* ── Metric Rows ── */
    .metric-row {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 8px;
        padding: 0.6rem 0.9rem;
        margin: 0.3rem 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.8rem;
        color: #9d98c0;
    }
    .metric-val {
        font-weight: 700;
        font-size: 0.88rem;
        font-family: 'DM Mono', monospace;
    }

    /* ── Section Headers ── */
    .section-label {
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: #7c77a0;
        margin-bottom: 1.2rem;
        display: flex;
        align-items: center;
        gap: 0.6rem;
    }
    .section-label-dot {
        width: 6px; height: 6px;
        border-radius: 50%;
        background: linear-gradient(135deg, #a78bfa, #60a5fa);
        flex-shrink: 0;
    }
    .section-header {
        font-size: 1.25rem;
        font-weight: 800;
        color: #f5f3ff;
        margin: 0.5rem 0 0.3rem;
        letter-spacing: -0.02em;
    }
    .section-sub { font-size: 0.82rem; color: #6d6a8a; margin-bottom: 1.2rem; }

    /* ── Insight Boxes ── */
    .insight-box {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin: 0.5rem 0;
        border-left: 3px solid;
        font-size: 0.86rem;
        color: #b8b4d0;
        line-height: 1.6;
    }
    .insight-dim {
        font-size: 0.62rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        margin-bottom: 0.4rem;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(255,255,255,0.03) !important;
        border-radius: 10px !important;
        padding: 4px !important;
        border: 1px solid rgba(255,255,255,0.07) !important;
        gap: 2px !important;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        border-radius: 7px !important;
        color: #7c77a0 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        padding: 0.45rem 1rem !important;
        transition: all 0.2s !important;
        border: none !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #c4b5fd !important;
        background: rgba(167,139,250,0.08) !important;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(167,139,250,0.18) !important;
        color: #c4b5fd !important;
    }
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 1.5rem !important;
    }

    /* ── Streamlit native overrides ── */
    .stMetric {
        background: rgba(255,255,255,0.03) !important;
        border: 1px solid rgba(255,255,255,0.06) !important;
        border-radius: 12px !important;
        padding: 1rem 1.2rem !important;
    }
    .stMetric label {
        color: #7c77a0 !important;
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.06em !important;
        text-transform: uppercase !important;
    }
    .stMetric [data-testid="stMetricValue"] {
        color: #f5f3ff !important;
        font-family: 'DM Mono', monospace !important;
        font-weight: 700 !important;
    }
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #a78bfa, #60a5fa) !important;
        border-radius: 3px !important;
    }
    .stProgress > div > div > div {
        background: rgba(255,255,255,0.07) !important;
        border-radius: 3px !important;
    }
    .stButton > button {
        background: rgba(255,255,255,0.04);
        color: #c4b5fd;
        border: 1px solid rgba(167,139,250,0.3);
        border-radius: 8px;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        padding: 0.55rem 1.2rem;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background: rgba(167,139,250,0.15);
        border-color: rgba(167,139,250,0.6);
        color: #e2d9ff;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, rgba(167,139,250,0.25), rgba(96,165,250,0.15));
        border-color: rgba(167,139,250,0.5);
        color: #e2d9ff;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, rgba(167,139,250,0.4), rgba(96,165,250,0.25));
        border-color: #a78bfa;
    }
    .stInfo {
        background: rgba(96,165,250,0.08) !important;
        border: 1px solid rgba(96,165,250,0.2) !important;
        border-radius: 8px !important;
        color: #93c5fd !important;
    }
    .stCaption { font-size: 0.74rem !important; color: #5a5578 !important; }

    /* ── Divider ── */
    .divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.07) 30%, rgba(255,255,255,0.07) 70%, transparent);
        margin: 2.5rem 0;
    }

    /* ── Footer ── */
    .km-footer {
        text-align: center;
        color: #4a4768;
        font-size: 0.76rem;
        padding: 1.5rem 0;
        border-top: 1px solid rgba(255,255,255,0.05);
        margin-top: 2rem;
        font-family: 'DM Mono', monospace;
    }

    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# CHARGEMENT DES DONNÉES
# ══════════════════════════════════════════════════════════════════════════════

def safe_float(v, default=0.0):
    if isinstance(v, (list, tuple)):
        v = v[0] if v else default
    try:
        f = float(v)
        return default if (f != f or f == float('inf')) else f
    except Exception:
        return default

def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.loads(f.read().strip() or json.dumps(default))
    except Exception:
        return default

feedbacks     = load_json("data/feedback.json",                [])
learning_log  = load_json("data/learning_log.json",            [])
gaps          = load_json("data/potential_gaps_realtime.json", [])
ragas_history = load_json("data/ragas_scores_history.json",    [])
ragas_scores  = load_json("data/ragas_scores.json",            {})
judge_log     = load_json("data/judge_log.json",               [])
history_conv  = load_json("data/historique.json",              [])
learned_faq   = load_json("data/raw/faq_auto_learned.json",    [])

try:
    from src.indexer import get_collection
    collection = get_collection()
    nb_docs    = collection.count()
except Exception:
    nb_docs = 0

nb_feedbacks  = len(feedbacks)
nb_positive   = len([f for f in feedbacks if f.get("rating") == "positive"])
nb_negative   = len([f for f in feedbacks if f.get("rating") == "negative"])
satisfaction  = (nb_positive / nb_feedbacks * 100) if nb_feedbacks > 0 else 0

nb_learned    = len([e for e in learning_log if e.get("status") == "success"])
nb_gaps       = len(gaps)
nb_gaps_open  = len([g for g in gaps if g.get("statut") == "non_traité"])
nb_gaps_done  = len([g for g in gaps if g.get("statut") in ("traité_auto", "traité")])
correction_rate = (nb_gaps_done / nb_gaps * 100) if nb_gaps > 0 else 0

nb_conv       = len(history_conv)
total_msgs    = sum(c.get("nb_messages", 0) for c in history_conv)
avg_msgs      = (total_msgs / nb_conv) if nb_conv > 0 else 0

sentiments    = [f.get("sentiment", "neutre") for f in feedbacks]
sent_counts   = Counter(sentiments)

ragas_score   = safe_float(ragas_scores.get("ragas_score", 0))
faithfulness  = safe_float(ragas_scores.get("faithfulness", 0))
answer_relev  = safe_float(ragas_scores.get("answer_relevancy", 0))
ctx_precision = safe_float(ragas_scores.get("context_precision", 0))

nb_judge      = len(judge_log)
judge_passed  = len([j for j in judge_log if j.get("verdict") == "pass"])
judge_rate    = (judge_passed / nb_judge * 100) if nb_judge > 0 else 0
avg_judge     = (sum(safe_float(j.get("global_score",0)) for j in judge_log) / nb_judge) if nb_judge > 0 else 0

improvements  = [e.get("improvement", 0) for e in learning_log if e.get("status") == "success" and e.get("improvement")]
avg_improve   = (sum(improvements) / len(improvements)) if improvements else 0

# ══════════════════════════════════════════════════════════════════════════════
# CALCUL KM HEALTH SCORE — SECI
# ══════════════════════════════════════════════════════════════════════════════
def clamp(v, mn=0, mx=100):
    return max(mn, min(mx, v))

escalation_rate  = len([f for f in feedbacks if f.get("sentiment") == "frustré"]) / max(nb_feedbacks, 1) * 100
engagement_score = min(avg_msgs / 6 * 100, 100)
s_score = clamp(satisfaction * 0.5 + (100 - escalation_rate) * 0.3 + engagement_score * 0.2)

gap_coverage  = clamp(correction_rate)
docs_richness = clamp(min(nb_docs / 50 * 100, 100))
e_score = clamp(gap_coverage * 0.6 + docs_richness * 0.4)

c_score = clamp(safe_float(ragas_score)*100*0.4 + safe_float(faithfulness)*100*0.35 + safe_float(ctx_precision)*100*0.25)
if ragas_score == 0 and nb_judge > 0:
    c_score = clamp(avg_judge * 100 * 0.8 + docs_richness * 0.2)

learn_volume  = clamp(min(nb_learned / 10 * 100, 100))
learn_quality = clamp(judge_rate)
learn_delta   = clamp(avg_improve * 500)
i_score = clamp(learn_volume * 0.35 + learn_quality * 0.40 + learn_delta * 0.25)

KM_SCORE = clamp(s_score * 0.25 + e_score * 0.20 + c_score * 0.35 + i_score * 0.20)

def get_level(score):
    if score >= 80: return ("Excellent", "#34d399", "🏆")
    if score >= 60: return ("Bon",        "#60a5fa", "✅")
    if score >= 40: return ("Moyen",      "#f59e0b", "⚠️")
    return              ("À améliorer",  "#fb7185", "🔴")

level_label, level_color, level_icon = get_level(KM_SCORE)

# ══════════════════════════════════════════════════════════════════════════════
# UI
# ══════════════════════════════════════════════════════════════════════════════

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
    <div class="page-header-eyebrow">HoodieWear KMS v3.0 · SECI Framework</div>
    <h1>KM Analytics</h1>
    <p>Dashboard de santé — Nonaka & Takeuchi (1995) · Score global pondéré sur 4 dimensions</p>
</div>
""", unsafe_allow_html=True)

last_update = ragas_scores.get("timestamp", "Jamais")
st.caption(f"Dernière évaluation RAGAS : {last_update}  ·  {nb_feedbacks} feedbacks  ·  {nb_docs} documents  ·  {nb_learned} apprentissages")

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION A — KM HEALTH SCORE
# ══════════════════════════════════════════════════════════════════════════════
col_score, col_seci = st.columns([1, 3], gap="large")

with col_score:
    st.markdown(f"""
    <div class="km-score-ring">
        <div class="km-score-glow" style="background:{level_color};"></div>
        <div class="km-score-label">KM Health Score</div>
        <div class="km-score-num" style="color:{level_color};">{KM_SCORE:.0f}</div>
        <div class="km-score-denom">/ 100</div>
        <div class="km-score-badge" style="background:{level_color}22;color:{level_color};border:1px solid {level_color}44;">
            {level_icon} &nbsp;{level_label}
        </div>
        <div class="km-score-breakdown">
            S <span>{s_score:.0f}</span> &nbsp;·&nbsp; E <span>{e_score:.0f}</span><br>
            C <span>{c_score:.0f}</span> &nbsp;·&nbsp; I <span>{i_score:.0f}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_seci:
    seci_data = [
        ("S", "Socialisation",   "Interactions client",
         s_score, "#fb7185",
         [("Satisfaction",      f"{satisfaction:.0f}%"),
          ("Taux d'escalade",   f"{escalation_rate:.0f}%"),
          ("Msgs / conv",       f"{avg_msgs:.1f}"),
          ("Conversations",     str(nb_conv))]),

        ("E", "Externalisation", "Gaps & couverture",
         e_score, "#f59e0b",
         [("Gaps détectés",    str(nb_gaps)),
          ("Gaps traités",     str(nb_gaps_done)),
          ("Correction rate",  f"{correction_rate:.0f}%"),
          ("Docs indexés",     str(nb_docs))]),

        ("C", "Combinaison",     "Qualité base RAG",
         c_score, "#60a5fa",
         [("RAGAS Score",      f"{ragas_score:.3f}"),
          ("Faithfulness",     f"{faithfulness:.3f}"),
          ("Ctx Precision",    f"{ctx_precision:.3f}"),
          ("Answer Relev.",    f"{answer_relev:.3f}")]),

        ("I", "Internalisation", "Apprentissage continu",
         i_score, "#34d399",
         [("Appris réussis",   str(nb_learned)),
          ("Taux judge",       f"{judge_rate:.0f}%"),
          ("Score judge",      f"{avg_judge:.2f}"),
          ("Amélioration moy", f"+{avg_improve:.3f}")]),
    ]

    cols4 = st.columns(4, gap="small")
    for col, (letter, title, sub, score, color, metrics) in zip(cols4, seci_data):
        pct = int(score)
        with col:
            rows_html = "".join([
                f'<div class="metric-row">'
                f'<span>{k}</span>'
                f'<span class="metric-val" style="color:{color};">{v}</span>'
                f'</div>'
                for k, v in metrics
            ])
            st.markdown(f"""
            <div class="seci-card">
                <div class="seci-card-top" style="background:linear-gradient(90deg,{color},{color}55);"></div>
                <div class="seci-card-glow" style="background:{color};"></div>
                <div class="seci-letter" style="color:{color};">{letter}</div>
                <div class="seci-title">{title}</div>
                <div class="seci-subtitle">{sub}</div>
                <div class="seci-score-num" style="color:{color};">{score:.0f}<span style="font-size:1rem;color:#5a5578;font-weight:400;">/100</span></div>
                <div class="seci-bar-bg">
                    <div class="seci-bar-fill" style="width:{pct}%;background:linear-gradient(90deg,{color},{color}88);"></div>
                </div>
                {rows_html}
            </div>
            """, unsafe_allow_html=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION B — MÉTRIQUES DÉTAILLÉES
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">Métriques détaillées</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">Vue complète de toutes les dimensions SECI</div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs([
    "💬  Interactions",
    "🧠  Apprentissage",
    "🔍  Qualité RAG",
    "📈  Évolution"
])

# ── Tab 1 : Interactions ───────────────────────────────────────────────────────
with tab1:
    col_i1, col_i2, col_i3 = st.columns(3)

    with col_i1:
        st.markdown('<div class="section-label"><span class="section-label-dot"></span>Feedbacks clients</div>', unsafe_allow_html=True)
        if nb_feedbacks > 0:
            st.progress(satisfaction / 100, text=f"Satisfaction : {satisfaction:.0f}% ({nb_positive}/{nb_feedbacks})")
            st.metric("👍 Positifs",  nb_positive)
            st.metric("👎 Négatifs",  nb_negative)
            st.metric("📊 Total",     nb_feedbacks)
        else:
            st.info("Aucun feedback encore.")

    with col_i2:
        st.markdown('<div class="section-label"><span class="section-label-dot"></span>Sentiments</div>', unsafe_allow_html=True)
        if sentiments:
            emoji_map = {"frustré": "😤", "satisfait": "😊", "urgent": "🚨", "confus": "🤔", "neutre": "😐"}
            color_map = {"frustré": "#fb7185", "satisfait": "#34d399", "urgent": "#f59e0b", "confus": "#a78bfa", "neutre": "#7c77a0"}
            for sent, cnt in sent_counts.most_common():
                pct_s = cnt / len(sentiments) * 100
                emoji = emoji_map.get(sent, "😐")
                color = color_map.get(sent, "#7c77a0")
                st.markdown(f"""
                <div class="metric-row">
                    <span>{emoji} {sent.capitalize()}</span>
                    <span class="metric-val" style="color:{color};">{cnt} ({pct_s:.0f}%)</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Aucune donnée sentiment.")

    with col_i3:
        st.markdown('<div class="section-label"><span class="section-label-dot"></span>Conversations</div>', unsafe_allow_html=True)
        st.metric("💬 Conversations",   nb_conv)
        st.metric("📨 Messages totaux", total_msgs)
        st.metric("📊 Moy. msgs/conv",  f"{avg_msgs:.1f}")

        if feedbacks:
            cutoff = datetime.now() - timedelta(days=7)
            recent = [f for f in feedbacks if f.get("date", "") >= cutoff.strftime("%Y-%m-%d")]
            st.metric("📅 Feedbacks 7j", len(recent))

        langs = Counter(f.get("langue", "french") for f in feedbacks)
        if langs:
            st.markdown('<div class="section-label" style="margin-top:1rem"><span class="section-label-dot"></span>Langues</div>', unsafe_allow_html=True)
            lang_flags = {"french": "🇫🇷", "english": "🇬🇧", "arabic": "🇹🇳"}
            for lang, cnt in langs.most_common():
                flag = lang_flags.get(lang, "🌍")
                st.caption(f"{flag} {lang.capitalize()} : {cnt}")

# ── Tab 2 : Apprentissage ──────────────────────────────────────────────────────
with tab2:
    col_l1, col_l2 = st.columns(2)

    with col_l1:
        st.markdown('<div class="section-label"><span class="section-label-dot"></span>Learning Pipeline</div>', unsafe_allow_html=True)
        st.metric("✅ Apprentissages réussis", nb_learned)

        total_attempts = len(learning_log)
        failed_learn   = len([e for e in learning_log if e.get("status") == "failed"])
        skipped_learn  = len([e for e in learning_log if e.get("status") == "skipped"])
        success_rate   = (nb_learned / total_attempts * 100) if total_attempts > 0 else 0

        if total_attempts > 0:
            st.progress(success_rate / 100, text=f"Taux de succès : {success_rate:.0f}%")
            st.metric("❌ Échoués",  failed_learn)
            st.metric("⏭️ Ignorés",  skipped_learn)
            st.metric("⏱️ Durée moy", f"{sum(e.get('duration_seconds',0) for e in learning_log)/total_attempts:.1f}s")

        topics = Counter(e.get("topic", "autre") for e in learning_log if e.get("status") == "success")
        if topics:
            st.markdown('<div class="section-label" style="margin-top:1rem"><span class="section-label-dot"></span>Topics appris</div>', unsafe_allow_html=True)
            topic_icons = {"livraison": "🚚", "retour": "↩️", "paiement": "💳", "taille": "📏", "commande": "📦", "entretien": "🧺", "compte": "👤", "general": "💬"}
            for topic, cnt in topics.most_common(5):
                icon = topic_icons.get(topic, "📌")
                st.markdown(f"""
                <div class="metric-row">
                    <span>{icon} {topic.capitalize()}</span>
                    <span class="metric-val" style="color:#34d399;">{cnt}</span>
                </div>
                """, unsafe_allow_html=True)

    with col_l2:
        st.markdown('<div class="section-label"><span class="section-label-dot"></span>Knowledge Gaps</div>', unsafe_allow_html=True)
        st.metric("🔍 Gaps détectés", nb_gaps)
        st.metric("✅ Gaps traités",   nb_gaps_done)
        st.metric("⏳ En attente",     nb_gaps_open)

        if nb_gaps > 0:
            st.progress(correction_rate / 100, text=f"Correction Rate : {correction_rate:.0f}%")

        open_gaps = [g for g in gaps if g.get("statut") == "non_traité"][-5:]
        if open_gaps:
            st.markdown('<div class="section-label" style="margin-top:1rem"><span class="section-label-dot" style="background:#f59e0b;"></span>Gaps en attente</div>', unsafe_allow_html=True)
            for g in reversed(open_gaps):
                score_g = g.get("score_rag", 0)
                color_g = "#fb7185" if score_g < 0.2 else "#f59e0b"
                st.markdown(f"""
                <div class="insight-box" style="border-left-color:{color_g};">
                    <span style="color:#5a5578;font-size:0.74rem;">{g.get('date','')[:10]}</span>
                    <span style="float:right;color:{color_g};font-weight:700;font-family:'DM Mono',monospace;">RAG:{score_g:.2f}</span><br>
                    {g.get('question','')[:80]}...
                </div>
                """, unsafe_allow_html=True)
            if st.button("🧠  Traiter les gaps →", key="goto_gaps"):
                st.switch_page("pages/7_KnowledgeGap.py")

# ── Tab 3 : Qualité RAG ────────────────────────────────────────────────────────
with tab3:
    col_r1, col_r2 = st.columns(2)

    with col_r1:
        st.markdown('<div class="section-label"><span class="section-label-dot"></span>Scores RAGAS</div>', unsafe_allow_html=True)
        if ragas_scores:
            metrics_ragas = [
                ("🎯 Faithfulness",      faithfulness,  "#fb7185"),
                ("💬 Answer Relevancy",  answer_relev,  "#60a5fa"),
                ("🔍 Context Precision", ctx_precision, "#f59e0b"),
                ("📚 Context Recall",    safe_float(ragas_scores.get("context_recall", 0)), "#34d399"),
            ]
            for label, val, color in metrics_ragas:
                pct_r = int(val * 100)
                st.markdown(f"""
                <div class="metric-row">
                    <span>{label}</span>
                    <span class="metric-val" style="color:{color};">{val:.3f}</span>
                </div>
                <div class="seci-bar-bg" style="margin-bottom:0.6rem;">
                    <div class="seci-bar-fill" style="width:{pct_r}%;background:{color};"></div>
                </div>
                """, unsafe_allow_html=True)
            st.metric("🏆 RAGAS Score global", f"{ragas_score:.3f}")
            st.caption(f"Évalué sur {ragas_scores.get('nb_questions','?')} questions · {ragas_scores.get('timestamp','?')}")
        else:
            st.info("Lancez une évaluation RAGAS dans la page Évaluation.")
            if st.button("🔬  Lancer l'évaluation →"):
                st.switch_page("pages/5_Evaluation.py")

    with col_r2:
        st.markdown('<div class="section-label"><span class="section-label-dot"></span>LLM Judge</div>', unsafe_allow_html=True)
        if nb_judge > 0:
            st.metric("⚖️ Évaluations",  nb_judge)
            st.metric("✅ Passed",        judge_passed)
            st.metric("📊 Taux succès",   f"{judge_rate:.0f}%")
            st.metric("🎯 Score moyen",   f"{avg_judge:.3f}")
            if nb_judge >= 5:
                st.progress(judge_rate / 100, text=f"Judge pass rate : {judge_rate:.0f}%")

            st.markdown('<div class="section-label" style="margin-top:1rem"><span class="section-label-dot"></span>Derniers verdicts</div>', unsafe_allow_html=True)
            for entry in reversed(judge_log[-5:]):
                v     = entry.get("verdict", "?")
                score = safe_float(entry.get("global_score", 0))
                icon  = "✅" if v == "pass" else "❌"
                color = "#34d399" if v == "pass" else "#fb7185"
                q     = entry.get("question", "")[:50]
                st.markdown(f"""
                <div class="metric-row">
                    <span style="font-size:0.78rem;">{icon} {q}...</span>
                    <span class="metric-val" style="color:{color};">{score:.2f}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Aucune évaluation judge encore. Posez des questions dans le chat.")

# ── Tab 4 : Évolution ──────────────────────────────────────────────────────────
with tab4:
    import pandas as pd

    if len(ragas_history) >= 2:
        st.markdown('<div class="section-label"><span class="section-label-dot"></span>Évolution RAGAS</div>', unsafe_allow_html=True)
        df_r = pd.DataFrame(ragas_history[-30:])
        for col_name in ["faithfulness", "answer_relevancy", "context_precision", "ragas_score"]:
            if col_name in df_r.columns:
                df_r[col_name] = df_r[col_name].apply(lambda x: safe_float(x))
        df_r["date"] = pd.to_datetime(df_r.get("date", df_r.index), errors="coerce")
        df_r = df_r.dropna(subset=["date"])
        cols_plot = [c for c in ["ragas_score", "faithfulness", "answer_relevancy", "context_precision"] if c in df_r.columns]
        if cols_plot:
            st.line_chart(df_r.set_index("date")[cols_plot])
            csv = df_r.reset_index().to_csv(index=False)
            st.download_button("⬇️  Exporter CSV", csv, "ragas_history.csv", "text/csv")
    else:
        st.info("Lancez au moins 2 évaluations RAGAS pour voir l'évolution.")

    if feedbacks:
        st.markdown('<div class="section-label" style="margin-top:1.5rem"><span class="section-label-dot"></span>Feedbacks / jour (30j)</div>', unsafe_allow_html=True)
        fb_by_day = Counter(f.get("date", "")[:10] for f in feedbacks if f.get("date", "")[:10])
        if fb_by_day:
            df_fb = pd.DataFrame([{"date": d, "feedbacks": c} for d, c in sorted(fb_by_day.items())[-30:]])
            df_fb["date"] = pd.to_datetime(df_fb["date"])
            st.line_chart(df_fb.set_index("date")["feedbacks"])

    if learning_log:
        st.markdown('<div class="section-label" style="margin-top:1.5rem"><span class="section-label-dot"></span>Apprentissages cumulés</div>', unsafe_allow_html=True)
        learn_by_day = {}
        for entry in learning_log:
            day = entry.get("timestamp", "")[:10]
            if day:
                learn_by_day[day] = learn_by_day.get(day, 0) + (1 if entry.get("status") == "success" else 0)
        if learn_by_day:
            df_learn = pd.DataFrame([{"date": d, "apprentissages": c} for d, c in sorted(learn_by_day.items())])
            df_learn["date"]    = pd.to_datetime(df_learn["date"])
            df_learn["cumulés"] = df_learn["apprentissages"].cumsum()
            st.line_chart(df_learn.set_index("date")["cumulés"])

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION C — INSIGHTS & RECOMMANDATIONS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">Insights & Recommandations</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">Actions prioritaires pour améliorer le KM Health Score</div>', unsafe_allow_html=True)

insights = []

if satisfaction < 60 and nb_feedbacks >= 5:
    insights.append(("🔴", "#fb7185", "Socialisation",
        f"Satisfaction faible ({satisfaction:.0f}%). Enrichissez les réponses et vérifiez les tons adaptatifs dans rag_chain.py."))
elif satisfaction >= 80:
    insights.append(("🟢", "#34d399", "Socialisation",
        f"Excellent taux de satisfaction : {satisfaction:.0f}%. Continuez à monitorer les feedbacks négatifs."))

if nb_gaps_open > 5:
    insights.append(("🟡", "#f59e0b", "Externalisation",
        f"{nb_gaps_open} gaps en attente. Lancez le batch learning dans la page KnowledgeGap."))
if nb_docs < 20:
    insights.append(("🔴", "#fb7185", "Combinaison",
        f"Seulement {nb_docs} documents indexés. Ajoutez des FAQ dans data/raw/ et réindexez."))

if faithfulness < 0.5 and ragas_score > 0:
    insights.append(("🔴", "#fb7185", "Combinaison",
        f"Faithfulness faible ({faithfulness:.2f}). Baissez temperature=0.1 dans rag_chain.py et enrichissez le contexte."))
if ctx_precision >= 0.8:
    insights.append(("🟢", "#34d399", "Combinaison",
        f"Context Precision excellente ({ctx_precision:.2f}). ChromaDB récupère les bons documents."))

if nb_learned == 0:
    insights.append(("🟡", "#f59e0b", "Internalisation",
        "Aucun apprentissage automatique encore. Les feedbacks 👎 déclenchent l'auto-learning — collectez plus de retours."))
elif avg_improve > 0.05:
    insights.append(("🟢", "#34d399", "Internalisation",
        f"Learning pipeline efficace : amélioration moyenne +{avg_improve:.3f}. {nb_learned} nouvelles connaissances indexées."))

if KM_SCORE < 40:
    insights.append(("🔴", "#fb7185", "Global",
        "Score KM faible. Priorité : indexer plus de documents et collecter des feedbacks."))
elif KM_SCORE >= 75:
    insights.append(("🟢", "#34d399", "Global",
        f"Système KM en bonne santé ({KM_SCORE:.0f}/100). Continuez à monitorer et améliorer la Faithfulness."))

if not insights:
    insights.append(("🔵", "#60a5fa", "Général",
        "Lancez des évaluations RAGAS et collectez des feedbacks pour obtenir des recommandations personnalisées."))

ins_cols = st.columns(2)
for i, (icon, color, dim, text) in enumerate(insights):
    with ins_cols[i % 2]:
        st.markdown(f"""
        <div class="insight-box" style="border-left-color:{color};">
            <div class="insight-dim" style="color:{color};">{icon}  {dim}</div>
            {text}
        </div>
        """, unsafe_allow_html=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION D — ACTIONS RAPIDES
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-label"><span class="section-label-dot"></span>Actions rapides</div>', unsafe_allow_html=True)

ac1, ac2, ac3, ac4 = st.columns(4)
with ac1:
    if st.button("🔬  Lancer éval. RAGAS", use_container_width=True, type="primary"):
        st.switch_page("pages/5_Evaluation.py")
with ac2:
    if st.button("🧠  Traiter les gaps", use_container_width=True):
        st.switch_page("pages/7_KnowledgeGap.py")
with ac3:
    if st.button("📁  Ajouter des docs", use_container_width=True):
        st.switch_page("pages/1_Admin.py")
with ac4:
    if st.button("🔄  Rafraîchir", use_container_width=True):
        st.rerun()

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="km-footer">
    HoodieWear KMS  &nbsp;·&nbsp; KM Health Score
    &nbsp;·&nbsp; Score actuel : <strong style="color:{level_color};">{KM_SCORE:.0f} / 100 &nbsp;{level_icon}</strong>
</div>
""", unsafe_allow_html=True)