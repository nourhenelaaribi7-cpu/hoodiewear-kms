import streamlit as st
import json
import os
from datetime import datetime
from src.auth import require_agent_or_admin

user = require_agent_or_admin()
st.set_page_config(page_title="Historique", page_icon="📜", layout="wide")

HISTORY_FILE = "data/historique.json"

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
        max-width: 1000px;
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

    /* ── Counter Card ── */
    .conv-count-card {
        background: rgba(167,139,250,0.07);
        border: 1px solid rgba(167,139,250,0.18);
        border-radius: 16px;
        padding: 1.8rem 2.2rem;
        display: inline-block;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
    }
    .conv-count-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(167,139,250,0.5), transparent);
    }
    .conv-count-label {
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: #7c77a0;
        margin-bottom: 0.5rem;
    }
    .conv-count-value {
        font-family: 'DM Mono', monospace;
        font-size: 4rem;
        font-weight: 500;
        line-height: 1;
        background: linear-gradient(135deg, #f5f3ff, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    /* ── Section Label ── */
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

    /* ── Expander (conversation cards) ── */
    .streamlit-expanderHeader {
        background: rgba(255,255,255,0.03) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-left: 3px solid rgba(167,139,250,0.5) !important;
        border-radius: 10px !important;
        padding: 1rem 1.3rem !important;
        font-family: 'DM Mono', monospace !important;
        font-size: 0.84rem !important;
        color: #c4b5fd !important;
        margin-bottom: 0.5rem !important;
        transition: background 0.2s, border-color 0.2s !important;
    }
    .streamlit-expanderHeader:hover {
        background: rgba(167,139,250,0.08) !important;
        border-left-color: #a78bfa !important;
    }
    .streamlit-expanderHeader[aria-expanded="true"] {
        background: rgba(167,139,250,0.1) !important;
        border-left-color: #a78bfa !important;
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
        margin-bottom: 0.5rem !important;
        padding: 0 !important;
    }

    /* ── Message blocks ── */
    .msg-block {
        padding: 1rem 1.4rem;
        border-bottom: 1px solid rgba(255,255,255,0.04);
        position: relative;
    }
    .msg-block:last-child { border-bottom: none; }
    .msg-role {
        font-size: 0.62rem;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        margin-bottom: 0.4rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }
    .msg-role::before {
        content: '';
        display: inline-block;
        width: 6px; height: 6px;
        border-radius: 50%;
        flex-shrink: 0;
    }
    .msg-role-user  {
        color: #60a5fa;
    }
    .msg-role-user::before  { background: #60a5fa; }
    .msg-role-bot   {
        color: #34d399;
    }
    .msg-role-bot::before   { background: #34d399; }
    .msg-content {
        font-size: 0.88rem;
        color: #b8b4d0;
        line-height: 1.65;
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
        padding: 0.55rem 1.4rem;
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
    .stButton > button[kind="secondary"] {
        border-color: rgba(251,113,133,0.4);
        color: #fb7185;
        background: rgba(251,113,133,0.05);
    }
    .stButton > button[kind="secondary"]:hover {
        background: rgba(251,113,133,0.15);
        border-color: rgba(251,113,133,0.7);
        color: #fda4af;
    }

    /* ── Success / Info messages ── */
    .stSuccess {
        background: rgba(52,211,153,0.1) !important;
        border: 1px solid rgba(52,211,153,0.25) !important;
        border-radius: 8px !important;
        color: #6ee7b7 !important;
    }

    /* ── Empty State ── */
    .empty-state {
        border: 1px dashed rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 4rem 2rem;
        text-align: center;
        background: rgba(255,255,255,0.02);
        margin-top: 2rem;
    }
    .empty-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
        opacity: 0.4;
        display: block;
    }
    .empty-text {
        color: #4a4768;
        font-size: 0.88rem;
        font-weight: 500;
    }

    /* ── Divider ── */
    .divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.07) 30%, rgba(255,255,255,0.07) 70%, transparent);
        margin: 2.5rem 0;
    }

    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Fonctions ─────────────────────────────────────────────────────────────────
def save_conversation(messages):
    os.makedirs("data", exist_ok=True)
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                history = json.loads(content) if content else []
        except Exception:
            history = []

    if messages:
        clean_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
        history.append({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "nb_messages": len(messages),
            "messages": clean_messages
        })
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history[-50:], f, ensure_ascii=False, indent=2)

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else []
    except Exception:
        return []

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
    <div class="page-header-eyebrow">Journal des sessions</div>
    <h1>Historique</h1>
    <p>50 dernières conversations sauvegardées</p>
</div>
""", unsafe_allow_html=True)

# ── Sauvegarder conversation courante ─────────────────────────────────────────
if "messages" in st.session_state and st.session_state.messages:
    if st.button("💾  Sauvegarder la conversation actuelle", type="primary"):
        save_conversation(st.session_state.messages)
        st.success("✓  Conversation sauvegardée avec succès.")

# ── Chargement ────────────────────────────────────────────────────────────────
history = load_history()

if not history:
    st.markdown("""
    <div class="empty-state">
        <span class="empty-icon">📭</span>
        <div class="empty-text">Aucune conversation sauvegardée pour le moment</div>
    </div>
    """, unsafe_allow_html=True)
else:
    # Compteur
    st.markdown(f"""
    <div class="conv-count-card">
        <div class="conv-count-label">Conversations sauvegardées</div>
        <div class="conv-count-value">{len(history):02d}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="section-label">
        <span class="section-label-dot"></span>
        Journal des échanges
    </div>
    """, unsafe_allow_html=True)

    for i, conv in enumerate(reversed(history)):
        nb_echanges = conv["nb_messages"] // 2
        label = f"📅  {conv['date']}   ·   {nb_echanges} échange{'s' if nb_echanges > 1 else ''}"

        with st.expander(label):
            for msg in conv["messages"]:
                if msg["role"] == "user":
                    st.markdown(f"""
                    <div class="msg-block">
                        <div class="msg-role msg-role-user">Client</div>
                        <div class="msg-content">{msg['content']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="msg-block">
                        <div class="msg-role msg-role-bot">Assistant</div>
                        <div class="msg-content">{msg['content']}</div>
                    </div>
                    """, unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    if st.button("🗑️  Effacer tout l'historique", type="secondary"):
        os.remove(HISTORY_FILE)
        st.success("✓  Historique effacé.")
        st.rerun()