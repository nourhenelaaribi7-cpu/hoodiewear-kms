import streamlit as st
import sys
import os
import json
import threading
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ── Import pipeline : LangGraph en priorité, fallback rag_chain ───────────────
try:
    from src.rag_pipeline import (
        answer_question_graph      as answer_question,
        answer_question_stream_graph as answer_question_stream,
    )
    PIPELINE_MODE = "langgraph"
except ImportError:
    from src.rag_chain import answer_question, answer_question_stream
    PIPELINE_MODE = "legacy"

from src.rag_chain import get_token_usage, suggest_followup_questions
from src.indexer   import index_documents, get_collection
from src.auth      import require_login, show_user_badge
from src.learning_pipeline import auto_learn_from_feedback

# ── Login ──────────────────────────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.logged_in:
    from src.auth import login_page
    st.markdown("""
    <div style="text-align:center; padding:40px 0 20px 0;">
        <div style="font-size:4rem;">👕</div>
        <h1 style="color:#1a1a2e; font-size:2.5rem; margin:0;">HoodieWear</h1>
        <p style="color:#666; font-size:1.1rem;">Smart Knowledge Management System</p>
        <p style="color:#e94560; font-size:0.9rem;">Powered by RAG + Llama 3.3 + ChromaDB</p>
    </div>
    """, unsafe_allow_html=True)
    login_page()
    st.stop()

user = st.session_state.user

# ── Fichiers ───────────────────────────────────────────────────────────────────
FEEDBACK_FILE = "data/feedback.json"
HISTORY_FILE  = "data/historique.json"

# ── Fonctions utilitaires ──────────────────────────────────────────────────────
def save_feedback(question, answer, rating, sentiment="neutre", language="french"):
    os.makedirs("data", exist_ok=True)
    feedbacks = []
    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                feedbacks = json.loads(content) if content else []
        except Exception:
            feedbacks = []

    feedbacks.append({
        "date":      datetime.now().strftime("%Y-%m-%d %H:%M"),
        "question":  question,
        "answer":    answer[:200],
        "rating":    rating,
        "sentiment": sentiment,
        "langue":    language
    })

    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(feedbacks, f, ensure_ascii=False, indent=2)

    if rating == "negative":
        lang_map   = {"french": "fr", "english": "en", "arabic": "ar"}
        lang_short = lang_map.get(language, "fr")

        def _learn_async():
            try:
                result = auto_learn_from_feedback(
                    question=question, bad_answer=answer, lang=lang_short
                )
                print(f"🧠 [Auto-Learn] {result['message']}")
            except Exception as e:
                print(f"🧠 [Auto-Learn] Erreur : {e}")

        thread = threading.Thread(target=_learn_async, daemon=True)
        thread.start()


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
        clean = [{"role": m["role"], "content": m["content"]} for m in messages]
        history.append({
            "date":        datetime.now().strftime("%Y-%m-%d %H:%M"),
            "nb_messages": len(messages),
            "messages":    clean
        })
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history[-50:], f, ensure_ascii=False, indent=2)


def load_feedbacks():
    if not os.path.exists(FEEDBACK_FILE):
        return []
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else []
    except Exception:
        return []


# ── Config page ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="HoodieWear Support IA",
    page_icon="👕",
    layout="wide"
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #fafafa; }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    [data-testid="stSidebar"] * { color: white !important; }
    [data-testid="stSidebar"] .stButton button {
        background: #e94560 !important; color: white !important;
        border: none !important; border-radius: 8px !important;
        font-weight: bold !important;
    }
    .hero-banner {
        background: linear-gradient(135deg, #1a1a2e 0%, #e94560 100%);
        padding: 30px 40px; border-radius: 16px;
        color: white; margin-bottom: 24px;
    }
    .hero-banner h1 { color: white; font-size: 2rem; margin: 0; }
    .hero-banner p  { color: rgba(255,255,255,0.85); margin: 8px 0 0 0; }
    .stat-card {
        background: white; border-radius: 12px; padding: 16px 20px;
        text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-top: 4px solid #e94560;
    }
    .stat-number { font-size: 2rem; font-weight: bold; color: #e94560; }
    .stat-label  { font-size: 0.85rem; color: #666; margin-top: 4px; }
    .stButton button {
        background: white !important; border: 2px solid #e94560 !important;
        color: #e94560 !important; border-radius: 20px !important;
        font-size: 0.85rem !important;
    }
    [data-testid="stChatMessage"] { border-radius: 12px; margin: 6px 0; padding: 4px; }
    .source-box {
        background: #f8f9fa; border-left: 4px solid #e94560;
        padding: 10px 14px; border-radius: 6px;
        font-size: 0.82em; margin: 6px 0; color: #444;
    }
    .score-badge {
        display: inline-block; background: #e94560; color: white;
        padding: 2px 8px; border-radius: 10px;
        font-size: 0.78em; font-weight: bold; margin-right: 8px;
    }
    .sentiment-badge {
        display: inline-block; padding: 3px 12px; border-radius: 12px;
        font-size: 0.78em; font-weight: bold; margin: 4px 0; color: white;
    }
    .judge-badge {
        display: inline-block; padding: 3px 10px; border-radius: 10px;
        font-size: 0.75em; font-weight: bold; margin: 2px;
    }
    .feedback-box {
        background: #f8f9fa; border-radius: 10px;
        padding: 10px 16px; margin-top: 8px; border: 1px solid #eee;
    }
    .suggestion-box {
        background: #fff8f9; border: 1px solid #e94560;
        border-radius: 10px; padding: 10px 14px; margin-top: 8px;
    }
    .escalade-box {
        background: #fff3cd; border: 2px solid #ff8800;
        border-radius: 10px; padding: 12px 16px; margin-top: 8px;
    }
    .learning-badge {
        display: inline-block; background: #1d9e75; color: white;
        padding: 3px 10px; border-radius: 12px;
        font-size: 0.78em; font-weight: bold; margin-top: 6px;
    }
    .pipeline-badge {
        display: inline-block; padding: 2px 8px; border-radius: 6px;
        font-size: 0.72em; font-weight: bold;
        background: #1a1a2e; color: #e94560; margin-left: 8px;
    }
    .footer {
        text-align: center; color: #aaa; font-size: 0.8rem;
        padding: 20px 0; border-top: 1px solid #eee; margin-top: 40px;
    }
    .rtl { direction: rtl; text-align: right; }
</style>
""", unsafe_allow_html=True)

# ── Init session state ─────────────────────────────────────────────────────────
for k, v in {
    "messages": [], "chat_history": [], "total_questions": 0,
    "scores_list": [], "sentiments_list": [], "judge_scores_list": []
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Textes multilingues ────────────────────────────────────────────────────────
LANGUES = {
    "🇫🇷 Français": {
        "titre":             "👕 HoodieWear — Assistant Service Client IA",
        "sous_titre":        "Notre IA répond à vos questions instantanément.",
        "faq_titre":         "💡 Questions fréquentes",
        "placeholder":       "💬 Posez votre question...",
        "spinner":           "🔍 Recherche en cours...",
        "feedback_q":        "Cette réponse vous a-t-elle aidé ?",
        "btn_oui":           "👍 Oui",
        "btn_non":           "👎 Non",
        "merci_pos":         "Merci pour votre retour ! 😊",
        "merci_neg":         "Merci ! Notre IA apprend de ce retour. 🧠",
        "nouvelle_conv":     "🗑️ Nouvelle conversation",
        "sauvegarder":       "💾 Sauvegarder",
        "sauvegarde_ok":     "✅ Sauvegardé !",
        "base_vide":         "⚠️ Base vide. Réindexez dans la sidebar.",
        "suggestions_suivi": "💡 Vous pourriez aussi demander :",
        "confiance_haute":   "🟢 Haute confiance",
        "confiance_moyenne": "🟡 Confiance moyenne",
        "confiance_faible":  "🔴 Faible confiance",
        "escalade_msg":      "🚨 Redirection vers un agent humain.",
        "learning_msg":      "🧠 L'IA apprend de ce retour en arrière-plan...",
        "suggestions": [
            "Quels sont les délais de livraison ?",
            "Comment retourner un article ?",
            "Comment suivre ma commande ?",
            "Quelles tailles sont disponibles ?",
            "Comment récupérer mon mot de passe ?",
            "Quels sont les modes de paiement ?",
            "Livrez-vous à l'international ?",
            "Puis-je annuler ma commande ?",
            "Comment laver mon hoodie ?",
        ]
    },
    "🇬🇧 English": {
        "titre":             "👕 HoodieWear — AI Customer Support",
        "sous_titre":        "Our AI answers your questions instantly.",
        "faq_titre":         "💡 Frequently Asked Questions",
        "placeholder":       "💬 Ask your question here...",
        "spinner":           "🔍 Searching knowledge base...",
        "feedback_q":        "Was this answer helpful?",
        "btn_oui":           "👍 Yes",
        "btn_non":           "👎 No",
        "merci_pos":         "Thank you for your feedback! 😊",
        "merci_neg":         "Thank you! Our AI is learning from this. 🧠",
        "nouvelle_conv":     "🗑️ New conversation",
        "sauvegarder":       "💾 Save",
        "sauvegarde_ok":     "✅ Saved!",
        "base_vide":         "⚠️ Empty database. Click Reindex.",
        "suggestions_suivi": "💡 You might also ask:",
        "confiance_haute":   "🟢 High confidence",
        "confiance_moyenne": "🟡 Medium confidence",
        "confiance_faible":  "🔴 Low confidence",
        "escalade_msg":      "🚨 Redirecting to a human agent.",
        "learning_msg":      "🧠 AI is learning from this feedback...",
        "suggestions": [
            "What are the delivery times?",
            "How do I return an item?",
            "How do I track my order?",
            "What sizes are available?",
            "How do I reset my password?",
            "What payment methods are accepted?",
            "Do you ship internationally?",
            "Can I cancel my order?",
            "How do I wash my hoodie?",
        ]
    },
    "🇹🇳 العربية": {
        "titre":             "👕 HoodieWear — مساعد خدمة العملاء",
        "sous_titre":        "يجيب الذكاء الاصطناعي على أسئلتك فوراً.",
        "faq_titre":         "💡 الأسئلة الشائعة",
        "placeholder":       "💬 اكتب سؤالك هنا...",
        "spinner":           "🔍 جاري البحث...",
        "feedback_q":        "هل كانت هذه الإجابة مفيدة؟",
        "btn_oui":           "👍 نعم",
        "btn_non":           "👎 لا",
        "merci_pos":         "شكراً على تقييمك! 😊",
        "merci_neg":         "شكراً! الذكاء الاصطناعي يتعلم من هذا. 🧠",
        "nouvelle_conv":     "🗑️ محادثة جديدة",
        "sauvegarder":       "💾 حفظ",
        "sauvegarde_ok":     "✅ تم الحفظ!",
        "base_vide":         "⚠️ قاعدة البيانات فارغة.",
        "suggestions_suivi": "💡 يمكنك أيضاً أن تسأل:",
        "confiance_haute":   "🟢 ثقة عالية",
        "confiance_moyenne": "🟡 ثقة متوسطة",
        "confiance_faible":  "🔴 ثقة منخفضة",
        "escalade_msg":      "🚨 تم التحويل إلى وكيل بشري.",
        "learning_msg":      "🧠 الذكاء الاصطناعي يتعلم في الخلفية...",
        "suggestions": [
            "ما هي مواعيد التسليم؟",
            "كيف أرجع منتجاً؟",
            "كيف أتتبع طلبيتي؟",
            "ما هي المقاسات المتاحة؟",
            "كيف أستعيد كلمة المرور؟",
            "ما هي طرق الدفع المقبولة؟",
            "هل تشحنون إلى تونس؟",
            "هل يمكنني إلغاء طلبيتي؟",
            "كيف أغسل الهودي؟",
        ]
    }
}

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 👕 HoodieWear KMS")
    st.markdown("*Smart Knowledge Management*")
    st.divider()

    show_user_badge()

    langue = st.selectbox(
        "🌍 Langue / Language / اللغة",
        list(LANGUES.keys()), index=0, key="langue_select"
    )
    T = LANGUES[langue]
    st.divider()

    # ── Pipeline badge ─────────────────────────────────────────────────────────
    if PIPELINE_MODE == "langgraph":
        st.markdown(
            '✅ **Pipeline** : <span style="color:#1d9e75;">LangGraph</span> actif',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '⚠️ **Pipeline** : <span style="color:#ff8800;">Legacy</span> (rag_chain)',
            unsafe_allow_html=True
        )
    st.divider()

    st.markdown("### 📚 Base de connaissances")
    try:
        collection = get_collection()
        count      = collection.count()
        st.success(f"✅ {count} documents indexés")
    except Exception:
        st.error("❌ ChromaDB non connecté")
        count = 0

    if st.button("🔄 Réindexer les données", use_container_width=True):
        with st.spinner("Indexation..."):
            try:
                index_documents()
                st.success("✅ Réussi !")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")

    st.divider()
    st.markdown("### ⚙️ Options")
    show_sources   = st.toggle("📄 Sources",      value=False)
    show_score     = st.toggle("📊 Score RAG",    value=True)
    show_sentiment = st.toggle("💬 Sentiment",    value=True)
    show_suggest   = st.toggle("💡 Suggestions",  value=True)
    show_judge     = st.toggle("⚖️ Score Judge",  value=True)
    use_stream     = st.toggle("⚡ Streaming",    value=True)
    st.divider()

    st.markdown("### 📈 Session")
    st.metric("Questions", st.session_state.total_questions)

    if st.session_state.scores_list:
        avg_rag = sum(st.session_state.scores_list) / len(st.session_state.scores_list)
        st.metric("Score RAG moyen", f"{avg_rag:.2f}")

    if st.session_state.judge_scores_list:
        avg_judge = sum(st.session_state.judge_scores_list) / len(st.session_state.judge_scores_list)
        color_j   = "🟢" if avg_judge >= 0.7 else "🟡" if avg_judge >= 0.5 else "🔴"
        st.metric("⚖️ Judge moyen", f"{color_j} {avg_judge:.2f}")

    if st.session_state.sentiments_list:
        from collections import Counter
        top   = Counter(st.session_state.sentiments_list).most_common(1)[0][0]
        emojis = {"frustré": "😤", "satisfait": "😊", "urgent": "🚨",
                  "confus": "🤔", "neutre": "😐"}
        st.metric("Sentiment dominant", f"{emojis.get(top,'😐')} {top}")

    feedbacks = load_feedbacks()
    if feedbacks:
        pos = len([f for f in feedbacks if f["rating"] == "positive"])
        st.metric("👍 Satisfaction", f"{pos}/{len(feedbacks)}")

    st.divider()
    st.markdown("### 🧠 Auto-Learning")
    try:
        from src.learning_pipeline import get_learning_stats
        ls = get_learning_stats()
        st.metric("Apprentissages réussis", ls["total_learned"])
        if ls["total_learned"] > 0:
            st.metric("Amélioration moyenne", f"+{ls['avg_improvement']:.3f}")
            st.caption(f"Taux de succès : {ls['success_rate']}%")
        if ls["last_learning"]:
            st.caption(f"Dernier : {ls['last_learning'][:16]}")
    except Exception:
        st.caption("Aucun apprentissage encore")

    st.divider()
    st.markdown("### 🔢 Tokens Groq")
    try:
        token_info = get_token_usage()
        color_tok  = "🔴" if token_info["critical"] else \
                     "🟡" if token_info["percent"] > 70 else "🟢"
        st.progress(
            token_info["percent"] / 100,
            text=f"{color_tok} {token_info['used']:,} / 100,000"
        )
        st.caption(f"Restants : {token_info['remaining']:,}")
        if token_info["critical"]:
            st.error("⚠️ Limite proche !")
    except Exception:
        pass

    st.divider()
    st.markdown("### 🛠️ Stack")
    pipeline_label = "LangGraph ✅" if PIPELINE_MODE == "langgraph" else "Legacy ⚠️"
    st.markdown(f"""
    - 🧠 **LLM** : Llama 3.3 (Groq)
    - 🔗 **Pipeline** : {pipeline_label}
    - ⚖️ **Judge** : LLM-as-a-Judge
    - 🔍 **RAG** : ChromaDB
    - 📐 **Embeddings** : MiniLM
    - 💬 **Sentiment** : Analyse IA
    - 🔄 **Learning** : Auto-feedback loop
    - 🖥️ **UI** : Streamlit
    """)
    st.caption("Smart Multimodal KMS v3.0")
    st.caption("HoodieWear © 2025")

# ── Hero ───────────────────────────────────────────────────────────────────────
rtl = "rtl" if langue == "🇹🇳 العربية" else ""
st.markdown(f"""
<div class="hero-banner {rtl}">
    <h1>{T['titre']} <span class="pipeline-badge">{PIPELINE_MODE.upper()}</span></h1>
    <p>{T['sous_titre']}</p>
</div>""", unsafe_allow_html=True)

# ── Stats cards ────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
avg_display = (
    f"{sum(st.session_state.scores_list)/len(st.session_state.scores_list):.2f}"
    if st.session_state.scores_list else "—"
)
avg_judge_display = (
    f"{sum(st.session_state.judge_scores_list)/len(st.session_state.judge_scores_list):.2f}"
    if st.session_state.judge_scores_list else "—"
)
pos_count = len([f for f in feedbacks if f["rating"] == "positive"]) if feedbacks else 0

for col, num, label in zip(
    [c1, c2, c3, c4, c5],
    [count, st.session_state.total_questions,
     avg_display, avg_judge_display, pos_count],
    ["Documents indexés", "Questions posées",
     "Score RAG moyen", "⚖️ Judge moyen", "👍 Feedbacks positifs"]
):
    with col:
        st.markdown(
            f'<div class="stat-card"><div class="stat-number">{num}</div>'
            f'<div class="stat-label">{label}</div></div>',
            unsafe_allow_html=True
        )

st.markdown("<br>", unsafe_allow_html=True)

# ── Suggestions initiales ──────────────────────────────────────────────────────
if len(st.session_state.messages) == 0:
    st.markdown(f"### {T['faq_titre']}")
    cols = st.columns(3)
    for i, s in enumerate(T["suggestions"]):
        with cols[i % 3]:
            if st.button(s, key=f"s{i}", use_container_width=True):
                st.session_state["pending"] = s
    st.divider()

# ── Historique chat ────────────────────────────────────────────────────────────
for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

        if msg["role"] == "assistant":

            # Sentiment
            if show_sentiment and msg.get("sentiment"):
                s = msg["sentiment"]
                st.markdown(
                    f'<span class="sentiment-badge" '
                    f'style="background:{s.get("color","#888")};">'
                    f'{s.get("emoji","😐")} {s.get("label","Neutre")}</span>',
                    unsafe_allow_html=True
                )

            # Escalade
            if msg.get("escalation"):
                st.markdown(
                    f'<div class="escalade-box">🚨 {T["escalade_msg"]}</div>',
                    unsafe_allow_html=True
                )

            # Score RAG
            if show_score and msg.get("avg_score", 0) > 0:
                sc  = msg["avg_score"]
                lbl = (T["confiance_haute"] if sc >= 0.7
                       else T["confiance_moyenne"] if sc >= 0.4
                       else T["confiance_faible"])
                st.progress(float(sc), text=f"{lbl} ({sc:.0%})")

            # ── NOUVEAU : Score Judge inline ───────────────────────────────────
            if show_judge and msg.get("judge") and msg["judge"].get("score", 0) > 0:
                j       = msg["judge"]
                j_score = j.get("score", 0)
                j_verd  = j.get("verdict", "?")
                j_color = "#1d9e75" if j_verd == "pass" else "#e94560"
                j_icon  = "✅" if j_verd == "pass" else "❌"
                st.markdown(
                    f'<span class="judge-badge" style="background:{j_color}22;'
                    f'color:{j_color};border:1px solid {j_color};">'
                    f'{j_icon} Judge : {j_score:.2f}</span>'
                    f'<span class="judge-badge" style="background:#f0f0f0;color:#666;">'
                    f'F:{j.get("faithfulness",0):.2f} '
                    f'R:{j.get("relevancy",0):.2f}</span>',
                    unsafe_allow_html=True
                )

            # Cache + langue
            lang_flags = {"french": "🇫🇷", "english": "🇬🇧", "arabic": "🇹🇳"}
            cm = st.columns([1, 1, 1, 4])
            with cm[0]: st.caption(f"🕐 {msg.get('time','')}")
            with cm[1]: st.caption(lang_flags.get(msg.get("language","french"), "🌍"))
            with cm[2]:
                if msg.get("from_cache"):
                    st.caption("💾 cache")

            # Sources
            if show_sources and msg.get("sources"):
                with st.expander("📄 Sources"):
                    for src in msg["sources"]:
                        st.markdown(f"""<div class='source-box'>
                            <span class='score-badge'>{src['score']}</span>
                            <b>Source :</b> {src['metadata'].get('source','').split('/')[-1]}<br><br>
                            {src['content'][:250]}...
                        </div>""", unsafe_allow_html=True)

            # Suggestions
            if show_suggest and msg.get("suggestions"):
                st.markdown(
                    f'<div class="suggestion-box">'
                    f'<small><b>{T["suggestions_suivi"]}</b></small></div>',
                    unsafe_allow_html=True
                )
                sc2 = st.columns(3)
                for i, sug in enumerate(msg["suggestions"]):
                    with sc2[i % 3]:
                        if st.button(sug, key=f"sug_{idx}_{i}",
                                     use_container_width=True):
                            st.session_state["pending"] = sug

            # Feedback
            fb_key = f"fb_done_{idx}"
            if fb_key not in st.session_state:
                st.markdown(
                    f"<div class='feedback-box'><small>{T['feedback_q']}</small></div>",
                    unsafe_allow_html=True
                )
                cl, cd, _ = st.columns([1, 1, 6])
                q_fb   = (st.session_state.messages[idx-1]["content"] if idx > 0 else "")
                s_fb   = msg.get("sentiment", {}).get("sentiment", "neutre")
                lang_fb = msg.get("language", "french")

                with cl:
                    if st.button(T["btn_oui"], key=f"like_{idx}"):
                        save_feedback(q_fb, msg["content"], "positive", s_fb, lang_fb)
                        st.session_state[fb_key] = "positive"
                        st.success(T["merci_pos"])
                        st.rerun()
                with cd:
                    if st.button(T["btn_non"], key=f"dislike_{idx}"):
                        save_feedback(q_fb, msg["content"], "negative", s_fb, lang_fb)
                        st.session_state[fb_key] = "negative"
                        st.warning(T["merci_neg"])
                        st.markdown(
                            f'<span class="learning-badge">{T["learning_msg"]}</span>',
                            unsafe_allow_html=True
                        )
                        st.rerun()
            else:
                icon    = "👍" if st.session_state[fb_key] == "positive" else "👎"
                learned = " · 🧠 appris" if st.session_state[fb_key] == "negative" else ""
                st.caption(f"{icon}{learned}")

# ── Input ──────────────────────────────────────────────────────────────────────
question = st.chat_input(T["placeholder"])
if "pending" in st.session_state:
    question = st.session_state.pop("pending")

# ── Traitement ─────────────────────────────────────────────────────────────────
if question:
    if count == 0:
        st.warning(T["base_vide"])
    else:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.write(question)

        with st.chat_message("assistant"):
            try:
                if use_stream:
                    result    = answer_question_stream(
                        question, st.session_state.chat_history)
                    answer    = st.write_stream(result["stream"])
                    meta      = result["metadata"]
                    sources   = meta.get("sources", [])
                    sentiment = meta.get("sentiment", {})
                    language  = meta.get("language", "french")
                    escalation = meta.get("escalation", False)
                    judge     = meta.get("judge", {})
                    avg_score = meta.get("avg_score", 0.0)
                else:
                    with st.spinner(T["spinner"]):
                        result = answer_question(
                            question, st.session_state.chat_history)
                    answer     = result["answer"]
                    st.write(answer)
                    sources    = result.get("sources", [])
                    sentiment  = result.get("sentiment", {})
                    language   = result.get("language", "french")
                    escalation = result.get("escalation", False)
                    judge      = result.get("judge", {})
                    avg_score  = result.get("avg_score", 0.0)

                now    = datetime.now().strftime("%H:%M")
                scores = [s["score"] for s in sources]
                avg_s  = sum(scores) / len(scores) if scores else avg_score

                # Sentiment badge
                if show_sentiment and sentiment:
                    st.markdown(
                        f'<span class="sentiment-badge" '
                        f'style="background:{sentiment.get("color","#888")};">'
                        f'{sentiment.get("emoji","😐")} '
                        f'{sentiment.get("label","Neutre")}</span>',
                        unsafe_allow_html=True
                    )

                # Escalade
                if escalation:
                    st.markdown(
                        f'<div class="escalade-box">🚨 {T["escalade_msg"]}</div>',
                        unsafe_allow_html=True
                    )

                # Score RAG
                if show_score and avg_s > 0:
                    lbl = (T["confiance_haute"] if avg_s >= 0.7
                           else T["confiance_moyenne"] if avg_s >= 0.4
                           else T["confiance_faible"])
                    st.progress(float(avg_s), text=f"{lbl} ({avg_s:.0%})")

                # ── NOUVEAU : Judge badge inline ───────────────────────────────
                if show_judge and judge and judge.get("score", 0) > 0:
                    j_score = judge.get("score", 0)
                    j_verd  = judge.get("verdict", "?")
                    j_color = "#1d9e75" if j_verd == "pass" else "#e94560"
                    j_icon  = "✅" if j_verd == "pass" else "❌"
                    st.markdown(
                        f'<span class="judge-badge" style="background:{j_color}22;'
                        f'color:{j_color};border:1px solid {j_color};">'
                        f'{j_icon} Judge : {j_score:.2f}</span>'
                        f'<span class="judge-badge" style="background:#f0f0f0;color:#666;">'
                        f'F:{judge.get("faithfulness",0):.2f} '
                        f'R:{judge.get("relevancy",0):.2f}</span>',
                        unsafe_allow_html=True
                    )

                lang_flags = {"french": "🇫🇷", "english": "🇬🇧", "arabic": "🇹🇳"}
                cm = st.columns([1, 1, 1, 4])
                with cm[0]: st.caption(f"🕐 {now}")
                with cm[1]: st.caption(lang_flags.get(language, "🌍"))
                with cm[2]:
                    if result.get("from_cache"):
                        st.caption("💾 cache")

                # Sources
                if show_sources and sources:
                    with st.expander("📄 Sources"):
                        for src in sources:
                            st.markdown(f"""<div class='source-box'>
                                <span class='score-badge'>{src['score']}</span>
                                <b>Source :</b>
                                {src['metadata'].get('source','').split('/')[-1]}<br><br>
                                {src['content'][:250]}...
                            </div>""", unsafe_allow_html=True)

                # Suggestions
                suggestions = result.get("suggestions") or \
                    (suggest_followup_questions(question, answer, language)
                     if show_suggest else [])

                if show_suggest and suggestions:
                    st.markdown(
                        f'<div class="suggestion-box">'
                        f'<small><b>{T["suggestions_suivi"]}</b></small></div>',
                        unsafe_allow_html=True
                    )
                    sc2 = st.columns(3)
                    for i, sug in enumerate(suggestions):
                        with sc2[i % 3]:
                            if st.button(sug, key=f"sug_new_{i}",
                                         use_container_width=True):
                                st.session_state["pending"] = sug

                # Sauvegarde message
                st.session_state.messages.append({
                    "role":        "assistant",
                    "content":     answer,
                    "sources":     sources,
                    "avg_score":   avg_s,
                    "time":        now,
                    "sentiment":   sentiment,
                    "suggestions": suggestions,
                    "language":    language,
                    "escalation":  escalation,
                    "judge":       judge,
                    "from_cache":  result.get("from_cache", False),
                })
                st.session_state.chat_history.extend([
                    {"role": "user",      "content": question},
                    {"role": "assistant", "content": answer}
                ])
                st.session_state.total_questions += 1
                st.session_state.scores_list.append(avg_s)

                # Track judge score
                if judge and judge.get("score", 0) > 0:
                    st.session_state.judge_scores_list.append(judge["score"])

                if sentiment:
                    st.session_state.sentiments_list.append(
                        sentiment.get("sentiment", "neutre"))
                st.rerun()

            except Exception as e:
                st.error(f"❌ Erreur : {str(e)}")

# ── Bas de page ────────────────────────────────────────────────────────────────
if st.session_state.messages:
    st.divider()
    col1, col2, _ = st.columns([1, 1, 4])
    with col1:
        if st.button(T["nouvelle_conv"]):
            save_conversation(st.session_state.messages)
            for k in ["messages", "chat_history", "scores_list",
                      "sentiments_list", "judge_scores_list"]:
                st.session_state[k] = []
            st.session_state.total_questions = 0
            for k in [k for k in st.session_state if k.startswith("fb_done_")]:
                del st.session_state[k]
            st.rerun()
    with col2:
        if st.button(T["sauvegarder"]):
            save_conversation(st.session_state.messages)
            st.success(T["sauvegarde_ok"])

st.markdown(f"""
<div class="footer">
    👕 HoodieWear Smart KMS v3.0 — RAG + Llama 3.3 (Groq) +
    ChromaDB + LangGraph + Judge IA + 🧠 Continuous Learning + Streamlit
    <br><span style="color:#e94560;">Pipeline : {PIPELINE_MODE.upper()}</span>
</div>""", unsafe_allow_html=True)