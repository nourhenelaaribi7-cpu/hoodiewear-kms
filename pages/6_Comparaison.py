# pages/6_Comparaison.py
import streamlit as st
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag_chain import answer_question, call_groq_llm

st.set_page_config(page_title="RAG vs Sans RAG", page_icon="⚖️", layout="wide")

st.title("⚖️ Comparaison — RAG vs Sans RAG")
st.caption("Démonstration concrète de l'apport du système RAG par rapport à un LLM seul.")
st.divider()

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