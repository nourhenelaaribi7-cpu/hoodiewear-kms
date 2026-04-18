import streamlit as st
import json
import os
from datetime import datetime

st.set_page_config(page_title="Historique", page_icon="📜", layout="wide")

HISTORY_FILE = "data/historique.json"

def save_conversation(messages):
    os.makedirs("data", exist_ok=True)
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                history = json.loads(content) if content else []
        except (json.JSONDecodeError, Exception):
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
    except (json.JSONDecodeError, Exception):
        return []

# ── UI ────────────────────────────────────────────────────────────────────────
st.title("📜 Historique des conversations")
st.caption("Les 50 dernières conversations sauvegardées.")

if "messages" in st.session_state and st.session_state.messages:
    if st.button("💾 Sauvegarder la conversation actuelle"):
        save_conversation(st.session_state.messages)
        st.success("✅ Conversation sauvegardée !")

st.divider()

history = load_history()

if not history:
    st.info("Aucune conversation sauvegardée pour le moment.")
else:
    st.markdown(f"**{len(history)} conversation(s) sauvegardée(s)**")
    
    for i, conv in enumerate(reversed(history)):
        with st.expander(f"🗨️ {conv['date']} — {conv['nb_messages']//2} échange(s)"):
            for msg in conv["messages"]:
                if msg["role"] == "user":
                    st.markdown(f"**🙋 Client :** {msg['content']}")
                else:
                    st.markdown(f"**🤖 Assistant :** {msg['content']}")
                st.divider()
    
    if st.button("🗑️ Effacer tout l'historique"):
        os.remove(HISTORY_FILE)
        st.success("Historique effacé !")
        st.rerun()