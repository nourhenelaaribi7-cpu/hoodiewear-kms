# pages/5_Evaluation.py
import streamlit as st
import sys
import os
import json
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="Évaluation RAG", page_icon="🔬", layout="wide")

SCORES_FILE = "data/evaluation_scores.json"

# ── Import modules ─────────────────────────────────────────────────────────────
try:
    from src.validator import load_scores_history, load_regression_alerts, TEST_QUESTIONS
    VALIDATOR_OK = True
except ImportError:
    VALIDATOR_OK = False
    TEST_QUESTIONS = []

try:
    from src.knowledge_gap import get_correction_rate
    KG_OK = True
except ImportError:
    KG_OK = False

st.title("🔬 Évaluation automatique — LLM-as-a-Judge")
st.caption("7 questions de test · Groq Llama 3.3 · Aucune clé OpenAI requise · 4 métriques")
st.divider()

# ── Explication métriques ──────────────────────────────────────────────────────
with st.expander("📖 Comprendre les 4 métriques"):
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("**🎯 Faithfulness**")
        st.caption("La réponse est-elle fidèle aux documents sources ? Détecte les hallucinations.")
    with c2:
        st.markdown("**💬 Answer Relevancy**")
        st.caption("La réponse répond-elle vraiment à la question posée ?")
    with c3:
        st.markdown("**🔍 Context Precision**")
        st.caption("Les documents récupérés par ChromaDB sont-ils pertinents ?")
    with c4:
        st.markdown("**📚 Complétude**")
        st.caption("La réponse couvre-t-elle toutes les informations attendues ?")
    st.info("**Méthode** : LLM-as-a-Judge — Llama 3.3 (Groq) note la qualité des réponses de 0 à 10. Aucune clé OpenAI requise.")

st.divider()

# ── Alertes de régression ──────────────────────────────────────────────────────
if VALIDATOR_OK:
    try:
        alerts = load_regression_alerts()
        if alerts:
            st.subheader("🚨 Alertes de régression")
            for alert in alerts[-5:]:
                severity_color = "🔴" if alert.get("severity") == "critique" else "🟡"
                st.warning(
                    f"{severity_color} **{alert['metric']}** : "
                    f"{alert['previous']} → {alert['current']} "
                    f"(↓ {alert['drop_pct']}%) — {alert.get('date','')}"
                )
            st.divider()
    except Exception:
        pass

# ── Bouton lancement ───────────────────────────────────────────────────────────
col_btn, col_info = st.columns([1, 3])
with col_btn:
    run_eval = st.button("🚀 Lancer l'évaluation", type="primary", use_container_width=True)
with col_info:
    st.info("⏱️ Durée estimée : 2-3 minutes pour 7 questions · Powered by Groq (gratuit)")

# ── Traitement évaluation ──────────────────────────────────────────────────────
if run_eval:
    progress_bar = st.progress(0, text="Initialisation...")
    status_text  = st.empty()

    def update_progress(i, total, question):
        pct = int((i / total) * 100)
        progress_bar.progress(pct, text=f"Question {i+1}/{total}")
        status_text.caption(f"🔍 {question[:60]}...")

    try:
        from src.evaluator import run_evaluation
        summary = run_evaluation(progress_callback=update_progress)
        progress_bar.progress(100, text="✅ Terminé !")
        status_text.empty()
        st.success(f"✅ Score global : {summary['global_score']:.0%}")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Erreur : {e}")

st.divider()

# ── Affichage résultats ────────────────────────────────────────────────────────
if os.path.exists(SCORES_FILE):
    try:
        with open(SCORES_FILE, "r", encoding="utf-8") as f:
            summary = json.load(f)

        st.subheader("📊 Résultats de la dernière évaluation")
        st.caption(
            f"🕐 {summary.get('date','—')} | "
            f"✅ {summary.get('nb_success','?')}/{summary.get('nb_questions','?')} questions réussies"
        )

        # ── Score global ───────────────────────────────────────────────────────
        gs    = summary.get("global_score", 0)
        color = "#00cc44" if gs >= 0.7 else "#ff8800" if gs >= 0.5 else "#ff4444"
        niveau = "Excellent 🏆" if gs >= 0.7 else "Correct ⚠️" if gs >= 0.5 else "À améliorer 🔴"

        st.markdown(f"""
        <div style="text-align:center;padding:24px;background:#f8f9fa;
                    border-radius:16px;margin:16px 0;border-top:6px solid {color};">
            <div style="font-size:3.5rem;font-weight:bold;color:{color};">{gs:.0%}</div>
            <div style="font-size:1.1rem;color:#444;margin-top:6px;">Score global — {niveau}</div>
            <div style="font-size:0.85rem;color:#aaa;">LLM-as-a-Judge · Groq Llama 3.3</div>
        </div>
        """, unsafe_allow_html=True)

        # ── 4 métriques ────────────────────────────────────────────────────────
        metrics = [
            ("🎯 Faithfulness",      summary.get("faithfulness", 0),      "Fidélité aux sources"),
            ("💬 Answer Relevancy",  summary.get("answer_relevancy", 0),  "Pertinence réponse"),
            ("🔍 Context Precision", summary.get("context_precision", 0), "Précision contexte"),
            ("📚 Complétude",        summary.get("completeness", 0),      "Couverture réponse"),
        ]

        # Correction Rate si disponible
        cols = st.columns(5 if KG_OK else 4)
        for col, (name, val, label) in zip(cols, metrics):
            c = "#00cc44" if val >= 0.7 else "#ff8800" if val >= 0.5 else "#ff4444"
            with col:
                st.markdown(f"""
                <div style="text-align:center;padding:16px;background:white;
                            border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.08);
                            border-top:4px solid {c};margin:4px;">
                    <div style="font-size:2rem;font-weight:bold;color:{c};">{val:.0%}</div>
                    <div style="font-size:0.85rem;font-weight:bold;margin-top:4px;">{name}</div>
                    <div style="font-size:0.75rem;color:#666;">{label}</div>
                </div>
                """, unsafe_allow_html=True)

        if KG_OK:
            with cols[4]:
                try:
                    cr_info = get_correction_rate()
                    cr_val  = cr_info["correction_rate"] / 100
                    cr_c    = "#00cc44" if cr_val >= 0.7 else "#ff8800" if cr_val >= 0.5 else "#ff4444"
                    st.markdown(f"""
                    <div style="text-align:center;padding:16px;background:white;
                                border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.08);
                                border-top:4px solid {cr_c};margin:4px;">
                        <div style="font-size:2rem;font-weight:bold;color:{cr_c};">🔄 {cr_val:.0%}</div>
                        <div style="font-size:0.85rem;font-weight:bold;margin-top:4px;">Correction Rate</div>
                        <div style="font-size:0.75rem;color:#666;">Lacunes corrigées</div>
                    </div>
                    """, unsafe_allow_html=True)
                except Exception:
                    st.metric("Correction Rate", "N/A")

        st.divider()

        # ── Barres de progression ──────────────────────────────────────────────
        st.subheader("📈 Détail des scores")
        for name, val, desc in metrics:
            col_l, col_r = st.columns([1, 3])
            with col_l:
                st.markdown(f"**{name}**")
                st.caption(desc)
            with col_r:
                st.progress(float(val), text=f"{val:.0%}")

        st.divider()

        # ── Interprétation ─────────────────────────────────────────────────────
        st.subheader("💡 Analyse & Recommandations")
        if gs >= 0.7:
            st.success("🟢 Votre système RAG est performant. Réponses fiables et pertinentes.")
        elif gs >= 0.5:
            st.warning("🟡 Le système est correct mais des améliorations sont possibles.")
        else:
            st.error("🔴 Le système nécessite des améliorations significatives.")

        if summary.get("faithfulness", 0) < 0.7:
            st.markdown("- 🎯 **Faithfulness faible** → Réduire `temperature=0.1` dans Groq")
        if summary.get("context_precision", 0) < 0.7:
            st.markdown("- 🔍 **Context Precision faible** → Augmenter `min_score=0.4` dans `retriever.py`")
        if summary.get("completeness", 0) < 0.7:
            st.markdown("- 📚 **Complétude faible** → Enrichir `data/raw/` avec plus de données")
        if summary.get("answer_relevancy", 0) < 0.7:
            st.markdown("- 💬 **Relevancy faible** → Améliorer le `SYSTEM_PROMPT` dans `rag_chain.py`")

        st.divider()

        # ── Graphique évolution ────────────────────────────────────────────────
        if VALIDATOR_OK:
            st.subheader("📈 Évolution des scores dans le temps")
            history = load_scores_history()
            if len(history) >= 2:
                df_hist = pd.DataFrame(history)
                if "date" in df_hist.columns:
                    df_hist["date"] = pd.to_datetime(df_hist["date"])
                    df_hist = df_hist.set_index("date")
                cols_plot = [c for c in
                             ["global_score", "faithfulness", "answer_relevancy",
                              "context_precision", "completeness"]
                             if c in df_hist.columns]
                if cols_plot:
                    st.line_chart(df_hist[cols_plot], y_label="Score (0-1)")
                csv = df_hist.reset_index().to_csv(index=False)
                st.download_button("⬇️ Exporter historique CSV", csv,
                                   "scores_history.csv", "text/csv")
            else:
                st.info("Lancez au moins 2 évaluations pour voir l'évolution.")

        st.divider()

        # ── Détail par question ────────────────────────────────────────────────
        st.subheader("📋 Résultats par question")
        details = summary.get("details", [])
        for i, item in enumerate(details):
            score   = item.get("global_score", 0)
            icon    = "🟢" if score >= 0.7 else "🟡" if score >= 0.5 else "🔴"
            with st.expander(f"{icon} Q{i+1} : {item['question']} — {score:.0%}"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**Réponse RAG :**")
                    st.info(item.get("answer", "N/A")[:400])
                with col_b:
                    st.markdown("**Réponse attendue :**")
                    st.success(item.get("ground_truth", "N/A"))
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Faithfulness",  f"{item.get('faithfulness',0):.0%}")
                c2.metric("Relevancy",     f"{item.get('answer_relevancy',0):.0%}")
                c3.metric("Precision",     f"{item.get('context_precision',0):.0%}")
                c4.metric("Complétude",    f"{item.get('completeness',0):.0%}")
                if "nb_sources" in item:
                    st.caption(
                        f"📄 {item['nb_sources']} sources | "
                        f"🎯 Score RAG : {item.get('avg_rag_score',0):.3f}"
                    )

    except Exception as e:
        st.error(f"Erreur lecture scores : {e}")
else:
    st.info("👆 Lancez l'évaluation pour voir les résultats.")

st.divider()
st.caption(
    "🔬 Méthode : LLM-as-a-Judge (Groq Llama 3.3 70B) · "
    "Inspiré de RAGAS — Es Sarraji et al., 2023 · "
    "Aucune clé OpenAI requise"
)