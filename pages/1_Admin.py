# pages/1_Admin.py 
import streamlit as st
import sys
import os
import json
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.indexer import index_documents, get_collection

st.set_page_config(page_title="Administration", page_icon="⚙️", layout="wide")

# ── CSS ───────────────────────────────────────────────────────────────────────
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
        background: #a78bfa;
        border-radius: 1px;
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
        width: 6px; height: 6px;
        border-radius: 50%;
        background: linear-gradient(135deg, #a78bfa, #60a5fa);
        flex-shrink: 0;
    }

    /* ── Alerts ── */
    .alert-critical {
        background: rgba(251,113,133,0.08);
        border: 1px solid rgba(251,113,133,0.25);
        border-left: 3px solid #fb7185;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.6rem;
        font-size: 0.86rem;
        color: #fda4af;
    }
    .alert-warning {
        background: rgba(251,191,36,0.06);
        border: 1px solid rgba(251,191,36,0.15);
        border-left: 3px solid rgba(251,191,36,0.6);
        border-radius: 8px;
        padding: 0.75rem 1.1rem;
        margin-bottom: 0.5rem;
        font-size: 0.83rem;
        color: #fde68a;
    }
    .alert-warning code {
        font-family: 'DM Mono', monospace;
        font-size: 0.8rem;
        background: rgba(251,191,36,0.1);
        padding: 0.1rem 0.4rem;
        border-radius: 4px;
        color: #fcd34d;
    }

    /* ── Metric Grid ── */
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 1rem;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 1.6rem 1.4rem;
        position: relative;
        overflow: hidden;
        transition: background 0.2s, border-color 0.2s;
    }
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(167,139,250,0.35), transparent);
    }
    .metric-card:hover {
        background: rgba(167,139,250,0.07);
        border-color: rgba(167,139,250,0.2);
    }
    .metric-glow {
        position: absolute;
        width: 60px; height: 60px;
        border-radius: 50%;
        top: -15px; right: -15px;
        filter: blur(25px);
        opacity: 0.12;
        background: #a78bfa;
    }
    .metric-label {
        font-size: 0.66rem;
        font-weight: 700;
        letter-spacing: 0.13em;
        text-transform: uppercase;
        color: #7c77a0;
        margin-bottom: 0.7rem;
    }
    .metric-value {
        font-size: 3.2rem;
        font-weight: 800;
        font-family: 'DM Mono', monospace;
        color: #f5f3ff;
        line-height: 1;
        letter-spacing: -0.02em;
    }
    .metric-sub {
        font-size: 0.72rem;
        color: #5a5578;
        margin-top: 0.4rem;
        font-family: 'DM Mono', monospace;
    }

    /* ── Feedback metric grid ── */
    .feedback-metric-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
        margin-bottom: 1.5rem;
    }

    /* ── Satisfaction bar ── */
    .satisfaction-bar-wrap {
        background: rgba(255,255,255,0.07);
        height: 6px;
        border-radius: 3px;
        margin: 0.6rem 0 1.5rem 0;
        overflow: hidden;
    }
    .satisfaction-bar-fill {
        height: 6px;
        background: linear-gradient(90deg, #a78bfa, #60a5fa);
        border-radius: 3px;
        transition: width 0.5s ease;
    }
    .satisfaction-label {
        font-size: 0.72rem;
        color: #7c77a0;
        font-family: 'DM Mono', monospace;
        margin-bottom: 0.3rem;
        font-weight: 500;
    }

    /* ── Buttons ── */
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
        color: #e2d9ff;
        border-color: rgba(167,139,250,0.5);
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, rgba(167,139,250,0.4), rgba(96,165,250,0.25));
        border-color: #a78bfa;
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

    /* ── Selectbox ── */
    .stSelectbox > div > div {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(167,139,250,0.25) !important;
        border-radius: 8px !important;
        color: #c8c4e0 !important;
        font-size: 0.85rem !important;
    }
    .stSelectbox > div > div:focus-within {
        border-color: rgba(167,139,250,0.6) !important;
    }

    /* ── File uploader ── */
    [data-testid="stFileUploader"] > div {
        background: rgba(255,255,255,0.02) !important;
        border: 1px dashed rgba(167,139,250,0.3) !important;
        border-radius: 12px !important;
        transition: border-color 0.2s !important;
    }
    [data-testid="stFileUploader"] > div:hover {
        border-color: rgba(167,139,250,0.6) !important;
        background: rgba(167,139,250,0.04) !important;
    }

    /* ── Progress bar ── */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #a78bfa, #60a5fa) !important;
        border-radius: 3px !important;
    }

    /* ── Expander ── */
    .streamlit-expanderHeader {
        background: rgba(255,255,255,0.03) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-left: 3px solid rgba(167,139,250,0.5) !important;
        border-radius: 10px !important;
        padding: 0.9rem 1.2rem !important;
        font-family: 'DM Mono', monospace !important;
        font-size: 0.84rem !important;
        color: #c4b5fd !important;
        margin-bottom: 0.4rem !important;
        transition: background 0.2s !important;
    }
    .streamlit-expanderHeader:hover {
        background: rgba(167,139,250,0.08) !important;
    }
    .streamlit-expanderHeader[aria-expanded="true"] {
        border-bottom-left-radius: 0 !important;
        border-bottom-right-radius: 0 !important;
        margin-bottom: 0 !important;
    }
    .streamlit-expanderContent {
        background: rgba(255,255,255,0.02) !important;
        border: 1px solid rgba(255,255,255,0.07) !important;
        border-top: none !important;
        border-left: 3px solid rgba(167,139,250,0.25) !important;
        border-bottom-left-radius: 10px !important;
        border-bottom-right-radius: 10px !important;
        margin-bottom: 0.4rem !important;
    }

    /* ── Success / Info / Error ── */
    .stSuccess {
        background: rgba(52,211,153,0.08) !important;
        border: 1px solid rgba(52,211,153,0.2) !important;
        border-radius: 8px !important;
        color: #6ee7b7 !important;
    }
    .stInfo {
        background: rgba(96,165,250,0.08) !important;
        border: 1px solid rgba(96,165,250,0.2) !important;
        border-radius: 8px !important;
        color: #93c5fd !important;
    }
    .stError {
        background: rgba(251,113,133,0.08) !important;
        border: 1px solid rgba(251,113,133,0.2) !important;
        border-radius: 8px !important;
        color: #fda4af !important;
    }

    /* ── Caption ── */
    .stCaption {
        font-size: 0.75rem !important;
        color: #5a5578 !important;
        letter-spacing: 0.02em !important;
    }

    /* ── Spinner ── */
    .stSpinner > div {
        border-color: #a78bfa transparent transparent !important;
    }

    /* ── Divider ── */
    .divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.07) 30%, rgba(255,255,255,0.07) 70%, transparent);
        margin: 2.5rem 0;
    }

    /* ── Section card wrap ── */
    .section-card {
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 16px;
        padding: 1.8rem;
        margin-bottom: 1.5rem;
        position: relative;
        overflow: hidden;
    }
    .section-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(167,139,250,0.2), transparent);
    }

    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

from src.auth import require_admin
user = require_admin()

FEEDBACK_FILE   = "data/feedback.json"
GAP_FAQ_FILE    = "data/raw/faq_auto_generated.json"
REGRESSION_FILE = "data/ragas_regression_alerts.json"

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
    <div class="page-header-eyebrow">HoodieWear KMS — v3.0</div>
    <h1>Administration</h1>
    <p>Gestion des documents, feedbacks et configuration du système</p>
</div>
""", unsafe_allow_html=True)

# ── Alertes RAGAS ─────────────────────────────────────────────────────────────
try:
    from src.validator import load_regression_alerts
    regression_alerts = load_regression_alerts()
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
        st.markdown(f"""
        <div class="alert-critical">
            ⚠️ &nbsp;<strong>{len(recent_alerts)} régression(s) RAGAS détectée(s)</strong> dans les dernières 48h —
            consultez la page Évaluation pour les détails.
        </div>
        """, unsafe_allow_html=True)
        for a in recent_alerts:
            st.markdown(f"""
            <div class="alert-warning">
                <strong>{a['metric']}</strong> &nbsp;
                <code>{a['previous']} → {a['current']}</code> &nbsp;
                ↓ {a['drop_pct']}% &nbsp;·&nbsp; {a['severity'].upper()}
            </div>
            """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
except ImportError:
    pass

# ── Section 1 : Upload ────────────────────────────────────────────────────────
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown("""
<div class="section-label">
    <span class="section-label-dot"></span>
    Documents
</div>
""", unsafe_allow_html=True)
st.caption("Formats acceptés : JSON · CSV · TXT")

uploaded_files = st.file_uploader(
    "Déposer des fichiers",
    type=["json", "csv", "txt"],
    accept_multiple_files=True,
    label_visibility="collapsed"
)

if uploaded_files:
    saved = []
    for file in uploaded_files:
        save_path = os.path.join("data/raw", file.name)
        os.makedirs("data/raw", exist_ok=True)
        with open(save_path, "wb") as f:
            f.write(file.read())
        saved.append(file.name)
    st.success(f"✓  {len(saved)} fichier(s) enregistré(s) : {', '.join(saved)}")
    if st.button("🔄  Réindexer", type="primary"):
        with st.spinner("Indexation en cours..."):
            try:
                index_documents()
                st.success("✓  Base réindexée avec succès.")
            except Exception as e:
                st.error(f"Erreur : {e}")

st.markdown('</div>', unsafe_allow_html=True)

# ── Section 2 : État de la base ───────────────────────────────────────────────
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown("""
<div class="section-label">
    <span class="section-label-dot"></span>
    Base de connaissances
</div>
""", unsafe_allow_html=True)

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

    feedbacks_raw = []
    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                feedbacks_raw = json.loads(content) if content else []
        except Exception:
            pass

    positifs_count = len([f for f in feedbacks_raw if f["rating"] == "positive"])

    correction_rate_val = "N/A"
    correction_rate_sub = ""
    try:
        from src.knowledge_gap import get_correction_rate
        cr = get_correction_rate()
        correction_rate_val = f"{cr['correction_rate']:.0f}%"
        correction_rate_sub = f"{cr['nb_corrected']}/{cr['nb_attempted']}"
    except Exception:
        pass

    st.markdown(f"""
    <div class="metric-grid">
        <div class="metric-card">
            <div class="metric-glow"></div>
            <div class="metric-label">Docs indexés</div>
            <div class="metric-value">{count}</div>
        </div>
        <div class="metric-card">
            <div class="metric-glow" style="background:#60a5fa;"></div>
            <div class="metric-label">Fichiers sources</div>
            <div class="metric-value">{len(raw_files)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-glow" style="background:#34d399;"></div>
            <div class="metric-label">Feedbacks positifs</div>
            <div class="metric-value" style="color:#34d399;">{positifs_count}</div>
            <div class="metric-sub">/ {len(feedbacks_raw)} total</div>
        </div>
        <div class="metric-card">
            <div class="metric-glow" style="background:#f59e0b;"></div>
            <div class="metric-label">Docs auto</div>
            <div class="metric-value">{len(auto_docs)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-glow" style="background:#818cf8;"></div>
            <div class="metric-label">Correction rate</div>
            <div class="metric-value">{correction_rate_val}</div>
            <div class="metric-sub">{correction_rate_sub}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if raw_files:
        file_data = []
        for fname in raw_files:
            fpath = os.path.join("data/raw", fname)
            size  = os.path.getsize(fpath)
            tag   = "auto" if "auto_generated" in fname else "manuel"
            file_data.append({
                "Fichier": fname,
                "Type": tag,
                "Taille (KB)": round(size / 1024, 1)
            })

        df_files = pd.DataFrame(file_data)
        st.dataframe(
            df_files,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Fichier": st.column_config.TextColumn("Fichier", width="large"),
                "Type": st.column_config.TextColumn("Type", width="small"),
                "Taille (KB)": st.column_config.NumberColumn(
                    "Taille (KB)", format="%.1f KB", width="small"
                ),
            }
        )

except Exception as e:
    st.error(f"ChromaDB : {e}")

st.markdown('</div>', unsafe_allow_html=True)

# ── Section 3 : Feedbacks ─────────────────────────────────────────────────────
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown("""
<div class="section-label">
    <span class="section-label-dot"></span>
    Feedbacks
</div>
""", unsafe_allow_html=True)

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
    taux     = len(positifs) / len(feedbacks) * 100

    st.markdown(f"""
    <div class="feedback-metric-grid">
        <div class="metric-card">
            <div class="metric-glow"></div>
            <div class="metric-label">Total feedbacks</div>
            <div class="metric-value">{len(feedbacks)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-glow" style="background:#34d399;"></div>
            <div class="metric-label">Positifs</div>
            <div class="metric-value" style="color:#34d399;">{len(positifs)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-glow" style="background:#fb7185;"></div>
            <div class="metric-label">Négatifs</div>
            <div class="metric-value" style="color:#fb7185;">{len(negatifs)}</div>
        </div>
    </div>
    <div class="satisfaction-label">Satisfaction — {taux:.0f}%</div>
    <div class="satisfaction-bar-wrap">
        <div class="satisfaction-bar-fill" style="width:{taux:.1f}%"></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="section-label" style="margin-top:1.5rem">
        <span class="section-label-dot" style="background:#fb7185;"></span>
        Derniers retours négatifs
    </div>
    """, unsafe_allow_html=True)

    for fb in negatifs[-5:]:
        with st.expander(f"📅  {fb['date']}  —  {fb['question'][:70]}"):
            st.markdown(f"**Question :** {fb['question']}")
            st.markdown(f"**Réponse :** {fb['answer']}")
            if st.button("🔧  Traiter cette lacune", key=f"goto_kg_{fb['date']}"):
                st.switch_page("pages/7_KnowledgeGap.py")
else:
    st.caption("Aucun feedback enregistré.")

st.markdown('</div>', unsafe_allow_html=True)

# ── Section 4 : Actions ───────────────────────────────────────────────────────
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown("""
<div class="section-label">
    <span class="section-label-dot"></span>
    Actions rapides
</div>
""", unsafe_allow_html=True)

col_a, col_b, col_c, col_d = st.columns(4)
with col_a:
    if st.button("🔄  Réindexer la base", use_container_width=True, type="primary"):
        with st.spinner("Réindexation..."):
            try:
                index_documents()
                st.success("✓  Réindexation terminée.")
            except Exception as e:
                st.error(f"Erreur : {e}")
with col_b:
    if st.button("🗑️  Vider les feedbacks", use_container_width=True):
        if os.path.exists(FEEDBACK_FILE):
            os.remove(FEEDBACK_FILE)
            st.success("✓  Feedbacks supprimés.")
            st.rerun()
with col_c:
    if st.button("🔍  Analyser les lacunes", use_container_width=True):
        st.switch_page("pages/7_KnowledgeGap.py")
with col_d:
    if st.button("📊  Évaluation RAGAS", use_container_width=True):
        st.switch_page("pages/5_Evaluation.py")

st.markdown('</div>', unsafe_allow_html=True)

# ── Section 5 : Audio ─────────────────────────────────────────────────────────
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.markdown("""
<div class="section-label">
    <span class="section-label-dot"></span>
    Traitement audio
</div>
""", unsafe_allow_html=True)
st.caption("Indexez un enregistrement d'appel ou message vocal directement dans la base.")

audio_file = st.file_uploader(
    "Fichier audio",
    type=["mp3", "wav", "mp4", "m4a", "ogg"],
    label_visibility="collapsed"
)

if audio_file:
    tmp_path = f"data/tmp_{audio_file.name}"
    os.makedirs("data", exist_ok=True)
    with open(tmp_path, "wb") as f:
        f.write(audio_file.read())

    col_lang, col_cat = st.columns(2)
    with col_lang:
        lang = st.selectbox("Langue", ["fr", "en", "ar"])
    with col_cat:
        cat = st.selectbox("Catégorie", [
            "support_client", "formation_agent",
            "reclamation", "livraison", "retour"
        ])

    if st.button("🎙️  Transcrire et indexer", type="primary"):
        with st.spinner("Transcription Whisper en cours..."):
            try:
                from src.audio_processor import process_audio_to_knowledge
                result = process_audio_to_knowledge(tmp_path, cat, lang)
                os.remove(tmp_path)
                st.success("✓  Audio transcrit et indexé avec succès.")
                st.info(f"**Transcription :** {result['question'][:300]}")
            except Exception as e:
                st.error(f"Erreur : {e}")

st.markdown('</div>', unsafe_allow_html=True)