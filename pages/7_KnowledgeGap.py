# pages/7_KnowledgeGap.py — Version 3.0 avec boucle de correction fermée
"""
Page 7 — Knowledge Gap Detector & Auto-amélioration
====================================================
Améliorations v3 :
  - Affichage du Correction Rate en temps réel
  - Score avant/après pour chaque lacune traitée
  - Re-génération automatique si correction échoue
  - Section "Lacunes prédictives" (module anticipatif)
  - Tableau de bord des corrections loggées
"""

import streamlit as st
import sys
import os
import json
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    background: white;
    border-radius: 14px;
    padding: 18px 22px;
    text-align: center;
    box-shadow: 0 2px 12px rgba(0,0,0,0.07);
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

# ── Titre ──────────────────────────────────────────────────────────────────────
st.title("🧠 Knowledge Gap Detector v3.0")
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
# SECTION 1 : KM Health Score — avec Correction Rate
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("🏥 KM Health Score")
st.caption("Métrique multi-dimensionnelle. La fraîcheur est désormais basée sur le Correction Rate réel.")

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
        ("🎯 Satisfaction client",       health["satisfaction"], "#e94560"),
        ("📚 Couverture des sujets",     health["couverture"],   "#3498db"),
        ("🔄 Fraîcheur (Correction Rate)", health["fraicheur"],  "#2ecc71"),
        ("⚡ Réactivité KM",             health["reactivite"],   "#f39c12"),
    ]
    for label, val, clr in dims:
        col_l, col_b = st.columns([1, 3])
        with col_l:
            st.markdown(f"<small style='color:#555'>{label}</small>", unsafe_allow_html=True)
        with col_b:
            st.progress(min(1.0, val / 100), text=f"{val:.0f}%")

# Métriques rapides — avec Correction Rate
st.markdown("")
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Lacunes ouvertes",   health["nb_gaps_ouverts"])
m2.metric("Lacunes traitées",   health["nb_gaps_traites"])
m3.metric("Docs auto-générés",  health["nb_auto_docs"])
m4.metric("Total feedbacks",    health["total_feedbacks"])
m5.metric("🎯 Correction Rate",
          f"{health['correction_rate']:.0f}%",
          delta=f"{health['nb_corrected']}/{health['nb_attempted']} corrigées")
m6.metric("📈 Delta score moyen",
          f"{health['avg_delta_score']:+.3f}",
          help="Amélioration moyenne du score RAG après correction")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 : Lacunes prédictives — NOUVEAU
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
                lang_flag  = {"fr": "🇫🇷", "en": "🇬🇧", "ar": "🇹🇳"}.get(gap.get("langue", "fr"), "🌍")
                freq       = gap.get("occurrences", 1)
                type_badge = (
                    "🔴 Feedback négatif" if gap.get("type") == "feedback_negatif"
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

                    col_gen, col_skip = st.columns([2, 1])
                    with col_gen:
                        if st.button("🤖 Générer une réponse IA", key=f"gen_{gap['id']}",
                                     type="primary", use_container_width=True):
                            with st.spinner("Génération en cours..."):
                                # Stocke le score avant pour la validation post-correction
                                gap["score_rag_avant"] = gap.get("score_rag", 0.0) or 0.0
                                new_entry = generate_answer_for_gap(gap, attempt=1)
                                if new_entry:
                                    st.session_state[f"gen_{gap['id']}"] = new_entry
                                    st.success("✅ Réponse générée ! Vérifiez ci-dessous.")
                                else:
                                    st.error("Erreur de génération. Réessayez.")

                    # Affiche la réponse générée
                    gen_key = f"gen_{gap['id']}"
                    if gen_key in st.session_state and isinstance(st.session_state[gen_key], dict):
                        entry = st.session_state[gen_key]
                        attempt = entry.get("attempt", 1)

                        if attempt > 1:
                            st.warning(f"⚠️ Tentative {attempt}/{MAX_REGEN_ATTEMPTS} "
                                       f"(la correction précédente n'a pas atteint le seuil)")

                        st.markdown("---")
                        st.markdown("**📝 Réponse générée par IA :**")
                        new_answer = st.text_area(
                            "Modifiez si nécessaire :",
                            value=entry["reponse"],
                            key=f"edit_{gap['id']}_{attempt}",
                            height=100
                        )
                        entry["reponse"] = new_answer

                        col_val, col_rej = st.columns(2)
                        with col_val:
                            if st.button("✅ Valider & Indexer", key=f"val_{gap['id']}_{attempt}",
                                         type="primary", use_container_width=True):
                                with st.spinner("Indexation + validation du score..."):
                                    result = approve_and_index_entry(entry)
                                    if result["success"]:
                                        val = result["validation"]
                                        delta_class = "delta-pos" if val["delta"] > 0 else "delta-neg"
                                        delta_str   = f"{val['delta']:+.3f}"

                                        if val["corrected"]:
                                            st.success(
                                                f"🎉 Lacune corrigée ! "
                                                f"Score : {val['score_before']} → {val['score_after']} "
                                                f"(Δ {delta_str})"
                                            )
                                            st.balloons()
                                        else:
                                            st.warning(
                                                f"⚠️ Indexé mais score insuffisant. "
                                                f"Score : {val['score_before']} → {val['score_after']} "
                                                f"(Δ {delta_str}) | Seuil : 0.55"
                                            )
                                            if result.get("needs_regen"):
                                                st.info("💡 Re-génération automatique avec prompt renforcé...")
                                                gap["score_rag_avant"] = val["score_after"]
                                                regen = generate_answer_for_gap(gap, attempt=2)
                                                if regen:
                                                    st.session_state[gen_key] = regen
                                                    st.info("🔄 Nouvelle version générée. Validez-la.")
                                                    st.rerun()

                                        del st.session_state[gen_key]
                                        st.rerun()
                                    else:
                                        st.error("Erreur lors de l'indexation.")

                        with col_rej:
                            if st.button("❌ Rejeter", key=f"rej_{gap['id']}_{attempt}",
                                         use_container_width=True):
                                del st.session_state[gen_key]
                                st.rerun()

    # ── Tab 2 : Lacunes traitées avec scores avant/après ──────────────────
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
                    delta_str   = f"{delta:+.3f}" if delta is not None else "N/A"
                    status_icon = "✅" if correction else "⚠️"
                    score_info  = (
                        f" | Score: {score_avant} → {score_apres} "
                        f"(Δ {delta_str}) {status_icon}"
                    )
                else:
                    score_info = ""

                st.markdown(
                    f"✅ **{gap['question'][:80]}...**"
                    f"<small style='color:#888'> — Traité le {gap.get('date_resolution', 'N/A')}"
                    f"{score_info}</small>",
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
            c1.metric("Corrections tentées", correction_info["nb_attempted"])
            c2.metric("Corrections réussies", correction_info["nb_corrected"])
            c3.metric("Correction Rate",
                      f"{correction_info['correction_rate']:.0f}%")
            c4.metric("Delta moyen",
                      f"{correction_info['avg_delta_score']:+.3f}")

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

            # Export CSV du log
            csv = df_log.to_csv(index=False, encoding="utf-8")
            st.download_button(
                "⬇️ Exporter le log des corrections (CSV)",
                csv,
                "correction_log.csv",
                "text/csv",
                use_container_width=False
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

    # Statistiques rapides sur les corrections
    corrected_count = sum(1 for d in auto_docs if d.get("score_rag_apres", 0) >= 0.55)
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

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 : Impact & Valeur ajoutée
# ══════════════════════════════════════════════════════════════════════════════
with st.expander("📈 Impact métier de ce module"):
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
        **Avant (v2) :**
        - ❌ Boucle ouverte : correction non vérifiée
        - ❌ Fraîcheur = volume (circulaire)
        - ❌ Groupement naïf par mots-clés
        - ❌ Aucune anticipation des lacunes
        - ❌ Aucun log des tentatives de correction
        """)
    with col_b:
        st.markdown("""
        **Après (v3) :**
        - ✅ Score RAG mesuré avant ET après
        - ✅ Correction Rate = métrique réelle
        - ✅ Déduplication sémantique par embeddings
        - ✅ Module prédictif sur 7 jours glissants
        - ✅ Log complet avec delta et tentatives
        """)

st.caption(
    "🧠 Knowledge Gap Detector v3.0 — HoodieWear Smart KMS | "
    "Nonaka & Takeuchi (1995) SECI | Boucle de correction fermée"
)