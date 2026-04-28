import streamlit as st
import json
import os
import pandas as pd
from src.auth import require_agent_or_admin

user = require_agent_or_admin()
st.set_page_config(page_title="Statistiques", page_icon="📊", layout="wide")

FEEDBACK_FILE = "data/feedback.json"
HISTORY_FILE  = "data/historique.json"

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #141428 50%, #0f0c29 100%);
        color: #e8e6f0;
        min-height: 100vh;
    }

    /* Background noise texture overlay */
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
    /* ── Page Header ── */
    .page-header {
        padding: 2.5rem 0 2rem 0;
        margin-bottom: 2.5rem;
        position: relative;
    }
    .page-header::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        width: 60px;
        height: 3px;
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
        width: 18px;
        height: 2px;
        background: #a78bfa;
        border-radius: 1px;
    }
    .page-header h1 {
        font-size: 3.4rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: #f5f3ff;
        margin: 0 0 0.4rem 0;
        line-height: 1;
        background: linear-gradient(135deg, #f5f3ff 0%, #c4b5fd 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .page-header p {
        font-size: 0.9rem;
        color: #6d6a8a;
        margin: 0;
        font-weight: 400;
    }

    /* ── Section Labels ── */
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
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: linear-gradient(135deg, #a78bfa, #60a5fa);
        flex-shrink: 0;
    }

    /* ── Metric Cards ── */
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
        margin-bottom: 2.5rem;
    }
    .metric-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 1.8rem 1.6rem;
        position: relative;
        overflow: hidden;
        transition: border-color 0.2s, background 0.2s;
    }
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(167,139,250,0.4), transparent);
    }
    .metric-card:hover {
        background: rgba(255,255,255,0.07);
        border-color: rgba(167,139,250,0.25);
    }
    .metric-card.positive::before {
        background: linear-gradient(90deg, transparent, rgba(52,211,153,0.5), transparent);
    }
    .metric-card.negative::before {
        background: linear-gradient(90deg, transparent, rgba(251,113,133,0.5), transparent);
    }
    .metric-glow {
        position: absolute;
        width: 80px;
        height: 80px;
        border-radius: 50%;
        top: -20px;
        right: -20px;
        filter: blur(30px);
        opacity: 0.15;
    }
    .glow-purple { background: #a78bfa; }
    .glow-blue   { background: #60a5fa; }
    .glow-green  { background: #34d399; }
    .glow-red    { background: #fb7185; }

    .metric-label {
        font-size: 0.68rem;
        font-weight: 600;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #7c77a0;
        margin-bottom: 0.8rem;
    }
    .metric-value {
        font-size: 3.8rem;
        font-weight: 800;
        font-family: 'DM Mono', monospace;
        color: #f5f3ff;
        line-height: 1;
        letter-spacing: -0.02em;
    }
    .metric-value.positive { color: #34d399; }
    .metric-value.negative { color: #fb7185; }
    .metric-sub {
        font-size: 0.75rem;
        color: #5a5578;
        margin-top: 0.5rem;
        font-weight: 500;
    }

    /* ── Chart Container ── */
    .chart-wrap {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 16px;
        padding: 1.8rem;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
    }
    .chart-wrap::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(96,165,250,0.4), transparent);
    }

    /* ── Dataframe ── */
    .stDataFrame {
        background: rgba(255,255,255,0.02) !important;
        border: 1px solid rgba(255,255,255,0.07) !important;
        border-radius: 12px !important;
        overflow: hidden !important;
    }
    .stDataFrame thead th {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 0.66rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.12em !important;
        text-transform: uppercase !important;
        color: #7c77a0 !important;
        background: rgba(255,255,255,0.04) !important;
        border-bottom: 1px solid rgba(255,255,255,0.07) !important;
        padding: 0.9rem 1rem !important;
    }
    .stDataFrame tbody td {
        font-family: 'DM Mono', monospace !important;
        font-size: 0.82rem !important;
        color: #c8c4e0 !important;
        padding: 0.75rem 1rem !important;
        border-bottom: 1px solid rgba(255,255,255,0.04) !important;
    }
    .stDataFrame tbody tr:hover td {
        background: rgba(167,139,250,0.06) !important;
    }

    /* ── Empty State ── */
    .empty-state {
        border: 1px dashed rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 3rem 2rem;
        text-align: center;
        color: #4a4768;
        font-size: 0.85rem;
        letter-spacing: 0.04em;
        margin-bottom: 2rem;
        background: rgba(255,255,255,0.02);
    }
    .empty-icon {
        font-size: 2.5rem;
        margin-bottom: 0.8rem;
        opacity: 0.4;
    }
    .empty-text {
        color: #4a4768;
        font-size: 0.85rem;
        font-weight: 500;
    }

    /* ── Divider ── */
    .divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.07) 30%, rgba(255,255,255,0.07) 70%, transparent);
        margin: 2.5rem 0;
    }

    /* Streamlit overrides */
    #MainMenu, footer, header { visibility: hidden; }

    /* Line chart color override */
    .stVegaLiteChart canvas, .stArrowVegaLiteChart canvas {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ── Chargement ────────────────────────────────────────────────────────────────
feedbacks = []
if os.path.exists(FEEDBACK_FILE):
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            feedbacks = json.loads(content) if content else []
    except Exception:
        feedbacks = []

history = []
if os.path.exists(HISTORY_FILE):
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            history = json.loads(content) if content else []
    except Exception:
        history = []

positifs  = [f for f in feedbacks if f["rating"] == "positive"]
negatifs  = [f for f in feedbacks if f["rating"] == "negative"]
taux_sat  = (len(positifs) / len(feedbacks) * 100) if feedbacks else 0

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
    <div class="page-header-eyebrow">Tableau de bord</div>
    <h1>Statistiques</h1>
    <p>Vue d'ensemble de l'activité, feedbacks et satisfaction utilisateurs</p>
</div>
""", unsafe_allow_html=True)

# ── Métriques globales ────────────────────────────────────────────────────────
total_msgs = sum(len(conv["messages"]) for conv in history) if history else 0

st.markdown(f"""
<div class="metric-grid">
    <div class="metric-card">
        <div class="metric-glow glow-purple"></div>
        <div class="metric-label">Conversations</div>
        <div class="metric-value">{len(history)}</div>
        <div class="metric-sub">{total_msgs} messages au total</div>
    </div>
    <div class="metric-card">
        <div class="metric-glow glow-blue"></div>
        <div class="metric-label">Feedbacks reçus</div>
        <div class="metric-value">{len(feedbacks)}</div>
        <div class="metric-sub">{len(positifs)} positifs · {len(negatifs)} négatifs</div>
    </div>
    <div class="metric-card positive">
        <div class="metric-glow glow-green"></div>
        <div class="metric-label">Satisfaction</div>
        <div class="metric-value positive">{taux_sat:.0f}%</div>
        <div class="metric-sub">Taux de satisfaction global</div>
    </div>
    <div class="metric-card negative">
        <div class="metric-glow glow-red"></div>
        <div class="metric-label">À améliorer</div>
        <div class="metric-value negative">{len(negatifs)}</div>
        <div class="metric-sub">Feedbacks négatifs</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Graphique satisfaction ────────────────────────────────────────────────────
st.markdown("""
<div class="chart-wrap">
""", unsafe_allow_html=True)

st.markdown("""
<div class="section-label">
    <span class="section-label-dot"></span>
    Évolution de la satisfaction
</div>
""", unsafe_allow_html=True)

if feedbacks:
    df = pd.DataFrame(feedbacks)
    df["date"] = pd.to_datetime(df["date"])
    df["positif"] = df["rating"] == "positive"
    daily = df.groupby(df["date"].dt.date)["positif"].mean() * 100
    st.line_chart(daily, y_label="% satisfaction", x_label="Date", color="#a78bfa")
else:
    st.markdown("""
    <div class="empty-state">
        <div class="empty-icon">📈</div>
        <div class="empty-text">Aucune donnée de satisfaction disponible</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ── Détail feedbacks ──────────────────────────────────────────────────────────
st.markdown("""
<div class="section-label">
    <span class="section-label-dot"></span>
    Détail des feedbacks
</div>
""", unsafe_allow_html=True)

if feedbacks:
    df_fb = pd.DataFrame(feedbacks)
    df_fb["date"] = pd.to_datetime(df_fb["date"])
    st.dataframe(
        df_fb[["date", "question", "rating"]].rename(columns={
            "date": "Date",
            "question": "Question",
            "rating": "Évaluation"
        }),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Date": st.column_config.DatetimeColumn("Date", format="YYYY-MM-DD HH:mm"),
            "Question": st.column_config.TextColumn("Question", width="large"),
            "Évaluation": st.column_config.TextColumn("Évaluation", width="small"),
        }
    )
else:
    st.markdown("""
    <div class="empty-state">
        <div class="empty-icon">📋</div>
        <div class="empty-text">Aucun feedback enregistré pour le moment</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ── Questions posées ──────────────────────────────────────────────────────────
st.markdown("""
<div class="section-label">
    <span class="section-label-dot"></span>
    Questions posées en session
</div>
""", unsafe_allow_html=True)

if history:
    all_questions = []
    for conv in history:
        for msg in conv["messages"]:
            if msg["role"] == "user":
                all_questions.append(msg["content"])

    if all_questions:
        df_q = pd.DataFrame({"Question": all_questions})
        st.dataframe(
            df_q,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Question": st.column_config.TextColumn("Question", width="large")
            }
        )
    else:
        st.caption("Aucune question trouvée dans l'historique.")
else:
    st.markdown("""
    <div class="empty-state">
        <div class="empty-icon">🔍</div>
        <div class="empty-text">Aucune conversation dans l'historique</div>
    </div>
    """, unsafe_allow_html=True)