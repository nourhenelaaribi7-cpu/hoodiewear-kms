# pages/8_Personnalisation.py 
"""
HoodieWear — Page Personnalisation 
"""
import streamlit as st
import sys, os
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.hoodie_customizer import (
    load_catalogue, recommander_taille, generer_apercu_svg,
    generer_recommendation_ia, COULEURS_CSS, GUIDE_TAILLES,
    build_images_dict, get_perso_examples, AGENT_STEPS, agent_generate_reco,
    debug_images_paths,
)

# ── Chargement images avec cache Streamlit (évite rechargement à chaque rerun) ─
@st.cache_resource(show_spinner="Chargement des images...")
def get_images():
    return build_images_dict()

@st.cache_resource(show_spinner=False)
def get_perso_imgs():
    return get_perso_examples()

IMAGES_PAR_MODELE = get_images()
 
with st.expander("Debug — chemins images (supprimer en production)", expanded=False):
    st.code(debug_images_paths())
    if st.button("Recharger les images"):
        get_images.clear()
        get_perso_imgs.clear()
        st.rerun()

st.set_page_config(
    page_title="HoodieWear — Personnalisation",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600&family=Space+Mono:wght@400;700&display=swap');
:root{--red:#e94560;--dark:#0f0f14;--dark2:#1a1a24;--dark3:#242430;
      --light:#f5f5f0;--gray:#888899;--green:#1d9e75;--gold:#f0c040;}
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;background:var(--dark)!important;color:var(--light)!important;}
[data-testid="stSidebar"],[data-testid="collapsedControl"]{display:none!important;}
::-webkit-scrollbar{width:4px}::-webkit-scrollbar-track{background:var(--dark2)}
::-webkit-scrollbar-thumb{background:var(--red);border-radius:2px}

/* Hero */
.hw-hero{background:linear-gradient(135deg,#0f0f14 0%,#1a0510 60%,#2d0818 100%);
  border:1px solid rgba(233,69,96,0.2);border-radius:20px;padding:44px 52px;
  position:relative;overflow:hidden;margin-bottom:32px;}
.hw-hero::after{content:'HW';position:absolute;bottom:-20px;right:40px;
  font-family:'Bebas Neue',cursive;font-size:140px;color:rgba(233,69,96,0.06);
  line-height:1;pointer-events:none;}
.hw-hero h1{font-family:'Bebas Neue',cursive;font-size:3.6rem;letter-spacing:3px;
  color:white;margin:0 0 8px;line-height:1;}
.hw-hero p{color:rgba(255,255,255,0.58);font-size:0.95rem;margin:0}
.pill{display:inline-block;background:var(--red);color:white;padding:4px 14px;
  border-radius:20px;font-size:0.72rem;font-weight:600;letter-spacing:1px;
  text-transform:uppercase;margin-bottom:14px;}

/* Sections */
.sec-title{font-family:'Bebas Neue',cursive;font-size:1.9rem;letter-spacing:2px;
  color:white;margin:0 0 4px;}
.sec-sub{color:var(--gray);font-size:0.82rem;margin-bottom:20px;}

/* Hide thumbnail nav buttons text */
.stButton > button[kind="secondary"] { display: none !important; }
div[data-testid="column"] > div > div > div > .stButton > button {
    height: 0px !important; padding: 0 !important; margin: 0 !important;
    border: none !important; background: transparent !important;
    position: absolute !important; opacity: 0 !important;
    width: 100% !important; cursor: pointer !important;
    z-index: 10 !important;
}
div[data-testid="column"] > div > div > div > .stButton {
    position: relative !important; margin-top: -38px !important;
    height: 38px !important; overflow: hidden !important;
}

/* Cards produit */
.prod-card{background:var(--dark2);border-radius:14px;overflow:hidden;
  border:1px solid rgba(255,255,255,0.06);transition:transform .2s,border-color .2s;}
.prod-card:hover{transform:translateY(-3px);border-color:rgba(233,69,96,0.35);}
.prod-card.selected{border-color:var(--red);border-width:1.5px;}
.prod-img{width:100%;height:230px;object-fit:cover;object-position:top center;display:block;}
.prod-info{padding:13px 15px 15px;}
.prod-name{font-family:'Bebas Neue',cursive;font-size:1.2rem;letter-spacing:1px;
  color:white;margin:0 0 4px;}
.prod-desc{color:var(--gray);font-size:0.78rem;margin:0 0 9px;line-height:1.5}
.prod-price{font-family:'Space Mono',monospace;font-size:1.25rem;color:var(--red);font-weight:700;}
.prod-rating{color:var(--gold);font-size:0.76rem;}
.badge-new{display:inline-block;background:var(--red);color:white;padding:3px 9px;
  border-radius:4px;font-size:0.66rem;font-weight:700;letter-spacing:1.5px;
  text-transform:uppercase;margin-bottom:7px;}
.swatch{display:inline-block;width:17px;height:17px;border-radius:50%;
  border:2px solid rgba(255,255,255,0.14);margin:2px;vertical-align:middle;}

/* Configurateur */
.config-panel{background:var(--dark2);border-radius:14px;padding:22px;
  border:1px solid rgba(255,255,255,0.06);}
.config-label{font-size:0.72rem;letter-spacing:1.5px;text-transform:uppercase;
  color:var(--gray);margin-bottom:7px;font-family:'Space Mono',monospace;}
.price-tag{font-family:'Space Mono',monospace;font-size:2.1rem;font-weight:700;color:var(--red);}
.price-base{font-size:0.80rem;color:var(--gray);}

/* Broderie panel */
.broder-panel{background:var(--dark3);border-radius:10px;padding:16px;
  border:1px solid rgba(255,255,255,0.05);margin-bottom:14px;}
.broder-example{background:var(--dark2);border-radius:8px;padding:8px;
  text-align:center;border:1px solid rgba(255,255,255,0.05);margin-top:8px;}
.broder-example img{width:100%;height:80px;object-fit:cover;border-radius:4px;}

/* Aperçu photo */
.photo-frame{border-radius:14px;overflow:hidden;height:370px;
  background:var(--dark3);position:relative;}
.photo-frame img{width:100%;height:100%;object-fit:cover;
  object-position:top center;display:block;}
.svg-container{background:linear-gradient(135deg,var(--dark3),var(--dark2));
  border-radius:14px;padding:22px 14px;text-align:center;
  border:1px solid rgba(255,255,255,0.06);min-height:370px;
  display:flex;align-items:center;justify-content:center;}

/* Panier */
.cart-item{background:var(--dark3);border-radius:9px;padding:11px 15px;
  margin:5px 0;display:flex;justify-content:space-between;align-items:center;
  border:1px solid rgba(255,255,255,0.05);}
.cart-total{font-family:'Space Mono',monospace;font-size:1.75rem;font-weight:700;color:var(--red);}

/* Chat agent */
.chat-wrap{background:var(--dark2) !important;border-radius:14px;overflow:hidden;
  border:1px solid rgba(255,255,255,0.08);}
.chat-header{padding:14px 18px;border-bottom:1px solid rgba(255,255,255,0.07);
  display:flex;align-items:center;gap:12px;background:var(--dark2);}
.agent-av{width:40px;height:40px;border-radius:50%;background:var(--red);
  display:flex;align-items:center;justify-content:center;color:white;
  font-weight:700;font-size:16px;flex-shrink:0;letter-spacing:0;}
.agent-name{font-size:0.9rem;font-weight:600;color:var(--light) !important;}
.agent-status{font-size:0.72rem;color:#2ecc71 !important;}
.chat-body{padding:18px 16px;max-height:340px;overflow-y:auto;
  display:flex;flex-direction:column;gap:12px;background:var(--dark2);}
.chat-body::-webkit-scrollbar{width:3px;}
.chat-body::-webkit-scrollbar-thumb{background:var(--red);border-radius:2px;}
.msg-agent{align-self:flex-start;background:var(--dark3) !important;
  border-radius:4px 14px 14px 14px;padding:12px 16px;font-size:0.85rem;
  line-height:1.65;color:var(--light) !important;max-width:82%;
  border:1px solid rgba(255,255,255,0.06);}
.msg-user{align-self:flex-end;background:var(--red) !important;
  border-radius:14px 4px 14px 14px;padding:12px 16px;
  font-size:0.85rem;line-height:1.65;color:white !important;max-width:78%;}
.reco-card{background:var(--dark2);border-radius:12px;padding:18px;
  border:1px solid rgba(233,69,96,0.25);margin-top:16px;}

/* Quick reply buttons custom style */
.quick-reply-btn > button {
  background: var(--dark3) !important;
  color: var(--light) !important;
  border: 1px solid rgba(255,255,255,0.12) !important;
  border-radius: 20px !important;
  font-size: 0.82rem !important;
  padding: 6px 14px !important;
  font-weight: 400 !important;
  transition: all .15s !important;
}
.quick-reply-btn > button:hover {
  border-color: var(--red) !important;
  color: var(--red) !important;
  background: var(--dark2) !important;
}

/* Misc Streamlit overrides */
[data-baseweb="tab-list"]{background:var(--dark2)!important;border-radius:10px!important;}
[data-baseweb="tab"]{color:var(--gray)!important;}
[aria-selected="true"]{color:white!important;}
.stTextInput input,.stTextArea textarea,.stNumberInput input{
  background:var(--dark3)!important;color:white!important;
  border-color:rgba(255,255,255,0.1)!important;}
.stSelectbox>div{background:var(--dark3)!important;color:white!important;}
.stButton>button{background:var(--red)!important;color:white!important;
  border:none!important;border-radius:10px!important;font-weight:600!important;}
.stButton>button:hover{opacity:0.85!important;}
hr{border-color:rgba(255,255,255,0.07)!important;}
[data-testid="metric-container"]{background:var(--dark2)!important;
  border-radius:10px!important;padding:12px!important;}
[data-testid="stExpander"]{background:var(--dark2)!important;
  border:1px solid rgba(255,255,255,0.06)!important;border-radius:10px!important;}
.hw-footer{text-align:center;color:var(--gray);font-size:0.75rem;
  padding:28px 0 14px;border-top:1px solid rgba(255,255,255,0.07);
  margin-top:44px;font-family:'Space Mono',monospace;}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
defaults = {
    "panier": [], "wishlist": [],
    "hoodie_sel": None, "taille_result": None,
    "config_couleur": "noir", "config_design": "uni",
    "config_taille": "M",
    "broder_type": "uni", "broder_texte": "", "broder_font": "serif",
    "reco_result": None,
    # Agent
    "agent_step": 0, "agent_ctx": {}, "agent_msgs": [],
    "agent_reco": None, "agent_done": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

catalogue = load_catalogue()

design_labels = {
    "uni": "Uni (sans design)", "logo_poitrine": "Logo HW poitrine",
    "logo_dos": "Logo dos", "broderie_poitrine": "Broderie poitrine (+5 DT)",
    "broderie_dos": "Broderie dos (+5 DT)", "print_poitrine": "Print poitrine",
    "print_dos": "Print dos", "bandes_laterales": "Bandes latérales",
    "texte_personnalise": "Texte personnalisé (+10 DT)",
}

broder_labels = {
    "uni": "Aucune (hoodie uni)", "initiales": "Initiales brodées (+8 DT)",
    "prenom": "Prénom brodé (+10 DT)", "date": "Date spéciale brodée (+10 DT)",
    "texte": "Texte libre brodé (+10 DT)", "logo": "Logo HW (inclus)",
}

# ══════════════════════════════════════════════════════════════════════════════
# HERO
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="hw-hero">
  <div class="pill">Collection 2025</div>
  <h1>PERSONNALISE<br>TON STYLE</h1>
  <p>Configurateur broderie · Guide tailles · Conseiller cadeau · Livraison Tunisie 3-5 jours</p>
</div>
""", unsafe_allow_html=True)

# Barre top
nb_items = len(st.session_state["panier"])
nb_wish  = len(st.session_state["wishlist"])
c1, c2, c3, c4 = st.columns([4, 1, 1, 1])
with c2:
    st.markdown(f'<div style="text-align:center;background:var(--dark2);border-radius:10px;padding:8px;border:1px solid rgba(255,255,255,0.06);"><div style="font-size:1.1rem;font-weight:700;color:var(--red);">{nb_items}</div><div style="font-size:0.7rem;color:var(--gray);">article(s)</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div style="text-align:center;background:var(--dark2);border-radius:10px;padding:8px;border:1px solid rgba(255,255,255,0.06);"><div style="font-size:1.1rem;font-weight:700;color:var(--red);">{nb_wish}</div><div style="font-size:0.7rem;color:var(--gray);">favori(s)</div></div>', unsafe_allow_html=True)
with c4:
    if st.button("Retour", key="back_btn"):
        st.switch_page("app.py")

st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — CATALOGUE
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec-title">COLLECTION</div>', unsafe_allow_html=True)
st.markdown('<div class="sec-sub">Sélectionnez un modèle · Naviguez entre les photos avec les miniatures</div>', unsafe_allow_html=True)

cf1, cf2, _ = st.columns([1, 1, 2])
with cf1:
    filtre_prix = st.selectbox("Prix", ["Tous", "< 90 DT", "90-120 DT", "> 120 DT"], key="filtre_prix")
with cf2:
    filtre_new = st.checkbox("Nouveautés seulement", key="filtre_new")

cat_filtree = catalogue.copy()
if filtre_new:
    cat_filtree = [h for h in cat_filtree if h.get("nouveaute")]
if filtre_prix == "< 90 DT":
    cat_filtree = [h for h in cat_filtree if h["prix"] < 90]
elif filtre_prix == "90-120 DT":
    cat_filtree = [h for h in cat_filtree if 90 <= h["prix"] <= 120]
elif filtre_prix == "> 120 DT":
    cat_filtree = [h for h in cat_filtree if h["prix"] > 120]

if not cat_filtree:
    st.info("Aucun modèle correspond aux filtres.")
else:
    cols_cat = st.columns(min(len(cat_filtree), 3), gap="medium")
    for col, hoodie in zip(cols_cat, cat_filtree):
        mk    = hoodie.get("image_placeholder", "classic")
        imgs  = IMAGES_PAR_MODELE.get(mk, [""])
        ikey  = f"cat_img_{hoodie['id']}"
        if ikey not in st.session_state:
            st.session_state[ikey] = 0

        with col:
            cur_img = imgs[st.session_state[ikey]] if imgs else ""
            is_wish = hoodie["id"] in st.session_state["wishlist"]
            is_sel  = st.session_state.get("hoodie_sel") and st.session_state["hoodie_sel"]["id"] == hoodie["id"]
            badge   = '<div class="badge-new">NOUVEAU</div><br>' if hoodie.get("nouveaute") else ""
            swatches = "".join([
                f'<span class="swatch" style="background:{COULEURS_CSS.get(c,"#888")};" title="{c}"></span>'
                for c in hoodie["couleurs_disponibles"][:8]
            ])
            sel_class = " selected" if is_sel else ""

            st.markdown(f"""
            <div class="prod-card{sel_class}">
              <div style="position:relative;">
                <img src="{cur_img}" class="prod-img" alt="{hoodie['nom']}"
                     onerror="this.parentElement.style.background='#242430';this.style.display='none'">
                <div style="position:absolute;top:10px;left:12px;">{badge}</div>
                <div style="position:absolute;top:10px;right:12px;background:rgba(0,0,0,0.65);
                            border-radius:6px;padding:3px 9px;font-family:'Space Mono',monospace;
                            font-size:0.76rem;color:white;">{hoodie['rating']} / 5</div>
              </div>
              <div class="prod-info">
                <div class="prod-name">{hoodie['nom']}</div>
                <div class="prod-desc">{hoodie['description'][:72]}...</div>
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:9px;">
                  <span class="prod-price">{hoodie['prix']} DT</span>
                  <span class="prod-rating">{hoodie['avis']} avis</span>
                </div>
                <div style="margin-bottom:9px;">{swatches}</div>
                <div style="font-size:0.70rem;color:rgba(255,255,255,0.30);
                            font-family:'Space Mono',monospace;">{hoodie['matiere'][:42]}</div>
              </div>
            </div>""", unsafe_allow_html=True)

            # Miniatures — images cliquables sans bouton visible
            n_imgs = min(len(imgs), 5)
            if n_imgs > 0:
                th_cols = st.columns(n_imgs)
                for ti, (tc, img_url) in enumerate(zip(th_cols, imgs[:5])):
                    with tc:
                        is_sel_th = st.session_state[ikey] == ti
                        bdr = "2px solid #e94560" if is_sel_th else "2px solid rgba(255,255,255,0.08)"
                        st.markdown(
                            f'<div style="border:{bdr};border-radius:5px;overflow:hidden;height:44px;">'
                            f'<img src="{img_url}" style="width:100%;height:100%;'
                            f'object-fit:cover;object-position:top center;display:block;"></div>',
                            unsafe_allow_html=True
                        )
                        if st.button(f"​", key=f"th_{hoodie['id']}_{ti}",
                                     use_container_width=True, help=f"Photo {ti+1}"):
                            st.session_state[ikey] = ti
                            st.rerun()

            ba1, ba2 = st.columns(2)
            with ba1:
                if st.button("Configurer", key=f"cfg_{hoodie['id']}", use_container_width=True):
                    st.session_state["hoodie_sel"]      = hoodie
                    st.session_state["config_couleur"]  = hoodie["couleurs_disponibles"][0]
                    st.session_state["config_design"]   = hoodie["designs_disponibles"][0]
                    st.session_state["config_taille"]   = (
                        "M" if "M" in hoodie["tailles_disponibles"]
                        else hoodie["tailles_disponibles"][0]
                    )
                    st.session_state["broder_type"]  = "uni"
                    st.session_state["broder_texte"] = ""
                    st.rerun()
            with ba2:
                wl = "Retirer" if is_wish else "Favoris"
                if st.button(wl, key=f"wish_{hoodie['id']}", use_container_width=True):
                    if hoodie["id"] in st.session_state["wishlist"]:
                        st.session_state["wishlist"].remove(hoodie["id"])
                    else:
                        st.session_state["wishlist"].append(hoodie["id"])
                    st.rerun()

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — CONFIGURATEUR (couleur + broderie + taille + aperçu)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec-title">CONFIGURATEUR</div>', unsafe_allow_html=True)
st.markdown('<div class="sec-sub">Choisissez couleur · broderie personnalisée · taille — aperçu en temps réel</div>', unsafe_allow_html=True)

hoodie_sel  = st.session_state.get("hoodie_sel") or catalogue[0]
noms_cat    = {h["nom"]: h for h in catalogue}
nom_choisi  = st.selectbox(
    "Modèle",
    list(noms_cat.keys()),
    index=list(noms_cat.keys()).index(hoodie_sel["nom"])
          if hoodie_sel["nom"] in noms_cat else 0,
    key="sel_modele"
)
hoodie_actif  = noms_cat[nom_choisi]
mk_cfg        = hoodie_actif.get("image_placeholder", "classic")
imgs_cfg      = IMAGES_PAR_MODELE.get(mk_cfg, [""])
cfg_img_key   = f"cfg_img_{mk_cfg}"
if cfg_img_key not in st.session_state:
    st.session_state[cfg_img_key] = 0

col_opt, col_prev = st.columns([1, 1], gap="large")

with col_opt:
    st.markdown('<div class="config-panel">', unsafe_allow_html=True)

    # ── Couleur ──────────────────────────────────────────────────────────────
    st.markdown('<div class="config-label">Couleur</div>', unsafe_allow_html=True)
    couleurs_dispo = hoodie_actif["couleurs_disponibles"]
    sw_html = "".join([
        f'<span class="swatch" style="background:{COULEURS_CSS.get(c,"#888")};" title="{c}"></span>'
        for c in couleurs_dispo
    ])
    st.markdown(f'<div style="margin-bottom:8px;">{sw_html}</div>', unsafe_allow_html=True)

    couleur_choisie = st.selectbox(
        "Couleur", couleurs_dispo,
        index=couleurs_dispo.index(st.session_state["config_couleur"])
              if st.session_state["config_couleur"] in couleurs_dispo else 0,
        format_func=lambda c: c.replace("_", " ").capitalize(),
        key="sel_couleur", label_visibility="collapsed"
    )
    st.session_state["config_couleur"] = couleur_choisie
    hex_c = COULEURS_CSS.get(couleur_choisie, "#888")
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">'
        f'<div style="width:28px;height:28px;border-radius:50%;background:{hex_c};'
        f'border:2px solid rgba(255,255,255,0.15);flex-shrink:0;"></div>'
        f'<code style="font-size:0.76rem;color:var(--gray);">{hex_c}</code></div>',
        unsafe_allow_html=True
    )

    # ── Broderie personnalisée ────────────────────────────────────────────────
    st.markdown('<div class="config-label">Personnalisation broderie</div>', unsafe_allow_html=True)
    st.markdown('<div class="broder-panel">', unsafe_allow_html=True)

    broder_type = st.radio(
        "Type de broderie",
        list(broder_labels.keys()),
        format_func=lambda k: broder_labels[k],
        index=list(broder_labels.keys()).index(st.session_state["broder_type"]),
        key="radio_broder",
        horizontal=False,
        label_visibility="collapsed"
    )
    st.session_state["broder_type"] = broder_type

    broder_texte = ""
    broder_font  = st.session_state["broder_font"]

    if broder_type != "uni" and broder_type != "logo":
        placeholders = {
            "initiales": "Ex : A, AB, S.M (max 2 car.)",
            "prenom":    "Ex : Sarah, Adam, Julie",
            "date":      "Ex : 14.02.2025",
            "texte":     "Ex : MON AMOUR, POUR TOI...",
        }
        maxlens = {"initiales": 2, "prenom": 12, "date": 14, "texte": 16}
        broder_texte = st.text_input(
            "Votre texte",
            value=st.session_state["broder_texte"],
            max_chars=maxlens.get(broder_type, 16),
            placeholder=placeholders.get(broder_type, "Votre texte"),
            key="inp_broder"
        )
        st.session_state["broder_texte"] = broder_texte

        broder_font = st.radio(
            "Police",
            ["serif", "block", "script"],
            format_func=lambda f: {"serif": "Serif élégant", "block": "Block gras", "script": "Script cursif"}[f],
            index=["serif","block","script"].index(st.session_state["broder_font"]),
            key="radio_font", horizontal=True, label_visibility="collapsed"
        )
        st.session_state["broder_font"] = broder_font

        # Note tarif
        tarif = {"initiales": "+8 DT", "prenom": "+10 DT", "date": "+10 DT", "texte": "+10 DT"}
        st.markdown(
            f'<div style="font-size:0.72rem;color:var(--gray);margin-top:4px;">'
            f'Supplément broderie : <strong style="color:var(--red);">{tarif.get(broder_type,"")}</strong></div>',
            unsafe_allow_html=True
        )

    st.markdown('</div>', unsafe_allow_html=True)  # fin broder-panel

    # Exemples de personnalisation
    perso_imgs = get_perso_imgs()
    if perso_imgs and broder_type != "uni":
        st.markdown('<div style="font-size:0.72rem;color:var(--gray);margin-bottom:6px;letter-spacing:1px;">EXEMPLES DE PERSONNALISATION</div>', unsafe_allow_html=True)
        ex_cols = st.columns(min(len(perso_imgs), 4))
        for ec, ep in zip(ex_cols, perso_imgs):
            with ec:
                st.markdown(
                    f'<div style="border-radius:6px;overflow:hidden;height:70px;">'
                    f'<img src="{ep}" style="width:100%;height:100%;object-fit:cover;object-position:top;display:block;"></div>',
                    unsafe_allow_html=True
                )

    # ── Taille ───────────────────────────────────────────────────────────────
    st.markdown('<div class="config-label" style="margin-top:14px;">Taille</div>', unsafe_allow_html=True)
    tailles_dispo = hoodie_actif["tailles_disponibles"]
    taille_choisie = st.select_slider(
        "Taille", options=tailles_dispo,
        value=st.session_state["config_taille"]
              if st.session_state["config_taille"] in tailles_dispo
              else tailles_dispo[0],
        key="sel_taille", label_visibility="collapsed"
    )
    st.session_state["config_taille"] = taille_choisie

    if taille_choisie in GUIDE_TAILLES:
        m = GUIDE_TAILLES[taille_choisie]
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Poitrine", f"{m['poitrine']} cm")
        mc2.metric("Epaules",  f"{m['epaules']} cm")
        mc3.metric("Longueur", f"{m['longueur']} cm")

    # ── Prix total ────────────────────────────────────────────────────────────
    st.markdown("---")
    prix_base = hoodie_actif["prix"]
    supp_broder = {"initiales": 8, "prenom": 10, "date": 10, "texte": 10}.get(broder_type, 0)
    prix_total  = prix_base + supp_broder

    st.markdown(
        f'<div style="display:flex;justify-content:space-between;align-items:flex-end;">'
        f'<div><div class="config-label">TOTAL</div>'
        f'<div class="price-tag">{prix_total} DT</div>'
        f'{"<div class=price-base>+" + str(supp_broder) + " DT broderie</div>" if supp_broder else ""}'
        f'</div>'
        f'<div style="text-align:right;color:var(--gray);font-size:0.76rem;">'
        f'Base : {prix_base} DT<br>{hoodie_actif["matiere"][:34]}</div>'
        f'</div>',
        unsafe_allow_html=True
    )
    st.markdown("<br>", unsafe_allow_html=True)

    btn1, btn2 = st.columns(2)
    with btn1:
        if st.button("Ajouter au panier", type="primary", use_container_width=True, key="btn_cart"):
            st.session_state["panier"].append({
                "id":           hoodie_actif["id"],
                "nom":          hoodie_actif["nom"],
                "couleur":      couleur_choisie,
                "hex":          hex_c,
                "broder_type":  broder_type,
                "broder_texte": broder_texte,
                "taille":       taille_choisie,
                "prix":         prix_total,
            })
            st.success(f"Ajouté : {hoodie_actif['nom']} taille {taille_choisie}")
    with btn2:
        is_wish_act = hoodie_actif["id"] in st.session_state["wishlist"]
        if st.button("Retirer des favoris" if is_wish_act else "Ajouter aux favoris",
                     use_container_width=True, key="btn_wish_cfg"):
            if is_wish_act:
                st.session_state["wishlist"].remove(hoodie_actif["id"])
                st.info("Retiré des favoris")
            else:
                st.session_state["wishlist"].append(hoodie_actif["id"])
                st.success("Ajouté aux favoris")

    st.markdown('</div>', unsafe_allow_html=True)  # fin config-panel

# ── Aperçu ────────────────────────────────────────────────────────────────────
with col_prev:
    tab_svg, tab_photo = st.tabs(["Aperçu personnalisé", "Photos réelles"])

    with tab_svg:
        svg_html = generer_apercu_svg(
            couleur=couleur_choisie,
            design=st.session_state["config_design"],
            texte=broder_texte,
            modele=mk_cfg,
            broder_type=broder_type,
            broder_texte=broder_texte,
            broder_font=broder_font,
        )
        st.markdown(f'<div class="svg-container">{svg_html}</div>', unsafe_allow_html=True)
        broder_str = (
            f" · {broder_labels.get(broder_type,'').split('(')[0].strip()}"
            + (f" : {broder_texte}" if broder_texte else "")
        ) if broder_type != "uni" else ""
        st.caption(f"{hoodie_actif['nom']} · {couleur_choisie.replace('_',' ').capitalize()} · {taille_choisie}{broder_str}")

    with tab_photo:
        idx_photo = st.session_state[cfg_img_key]
        main_img  = imgs_cfg[idx_photo] if imgs_cfg else ""

        st.markdown(
            f'<div class="photo-frame">'
            f'<img src="{main_img}" alt="{hoodie_actif["nom"]}" '
            f'onerror="this.style.display=\'none\';this.parentElement.style.background=\'#242430\'">'
            f'</div>',
            unsafe_allow_html=True
        )
        st.caption(f"Photo {idx_photo+1} / {len(imgs_cfg)} — {hoodie_actif['nom']}")

        # Miniatures navigation configurateur
        if len(imgs_cfg) > 1:
            th2_cols = st.columns(min(len(imgs_cfg), 5))
            for ti, (tc, img_url) in enumerate(zip(th2_cols, imgs_cfg[:5])):
                with tc:
                    is_s = (st.session_state[cfg_img_key] == ti)
                    bdr  = "2px solid #e94560" if is_s else "2px solid rgba(255,255,255,0.08)"
                    st.markdown(
                        f'<div style="border:{bdr};border-radius:5px;overflow:hidden;height:46px;">'
                        f'<img src="{img_url}" style="width:100%;height:100%;object-fit:cover;object-position:top center;display:block;"></div>',
                        unsafe_allow_html=True
                    )
                    if st.button(f"​", key=f"cfg_th_{ti}",
                                 use_container_width=True, help=f"Photo {ti+1}"):
                        st.session_state[cfg_img_key] = ti
                        st.rerun()

        # Info matière
        st.markdown(
            f'<div style="margin-top:12px;padding:12px 15px;background:var(--dark3);'
            f'border-radius:9px;border:1px solid rgba(255,255,255,0.05);">'
            f'<div style="font-size:0.70rem;color:var(--gray);letter-spacing:1.5px;'
            f'text-transform:uppercase;margin-bottom:4px;">Matière</div>'
            f'<div style="font-size:0.88rem;">{hoodie_actif["matiere"]}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — GUIDE TAILLES
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec-title">GUIDE DES TAILLES</div>', unsafe_allow_html=True)
st.markdown('<div class="sec-sub">Calculateur morphologie + tableau complet</div>', unsafe_allow_html=True)

col_form, col_res = st.columns([1, 1], gap="large")
with col_form:
    with st.form("form_taille"):
        t_h  = st.slider("Taille (cm)", 145, 215, 175)
        t_w  = st.slider("Poids (kg)", 40, 160, 70)
        t_tp = st.number_input("Tour de poitrine (cm) — 0 = calcul auto", 0, 160, 0)
        t_st = st.radio("Style préféré",
                        ["regular", "fitted", "oversized"],
                        format_func=lambda s: {"regular":"Regular","fitted":"Fitted","oversized":"Oversized"}[s],
                        horizontal=True)
        if st.form_submit_button("Calculer ma taille", type="primary", use_container_width=True):
            st.session_state["taille_result"] = recommander_taille(t_h, t_w, t_tp or None, t_st)

with col_res:
    if st.session_state.get("taille_result"):
        r = st.session_state["taille_result"]
        st.markdown(f"""
        <div style="text-align:center;background:var(--dark2);border-radius:14px;
                    padding:26px;border:1px solid rgba(233,69,96,0.3);margin-bottom:14px;">
          <div style="font-size:0.70rem;color:var(--gray);letter-spacing:2px;
                      text-transform:uppercase;font-family:Space Mono,monospace;margin-bottom:8px;">
            TAILLE RECOMMANDEE</div>
          <div style="font-family:Bebas Neue,cursive;font-size:5rem;color:var(--red);line-height:1;">
            {r['taille']}</div>
          <div style="color:rgba(255,255,255,0.5);font-size:0.83rem;margin-top:8px;">{r['note_style']}</div>
        </div>""", unsafe_allow_html=True)
        if r["alternatives"]:
            st.markdown("**Alternatives :** " + " ".join([f'`{t}`' for t in r["alternatives"]]))
        st.markdown(f'<div style="background:var(--dark3);border-radius:9px;padding:13px 15px;font-size:0.86rem;color:rgba(255,255,255,0.58);line-height:1.7;">{r["explication"]}</div>', unsafe_allow_html=True)
        m = r["mesures"]
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Poitrine", f"{m['poitrine']} cm")
        mc2.metric("Epaules",  f"{m['epaules']} cm")
        mc3.metric("Longueur", f"{m['longueur']} cm")
        if st.button("Utiliser cette taille", use_container_width=True):
            st.session_state["config_taille"] = r["taille"]
            st.success(f"Taille {r['taille']} appliquée !")
    else:
        st.markdown("""
        <div style="background:var(--dark2);border-radius:14px;padding:36px;text-align:center;
                    color:var(--gray);border:1px solid rgba(255,255,255,0.05);">
          <div style="font-family:Bebas Neue,cursive;font-size:1.4rem;letter-spacing:2px;">TROUVEZ VOTRE TAILLE</div>
          <div style="font-size:0.83rem;margin-top:8px;">Remplissez le formulaire pour une recommandation personnalisée</div>
        </div>""", unsafe_allow_html=True)

with st.expander("Voir le tableau des tailles complet"):
    import pandas as pd
    df = pd.DataFrame([
        {"Taille": t, "Poitrine (cm)": m["poitrine"], "Epaules (cm)": m["epaules"], "Longueur (cm)": m["longueur"]}
        for t, m in GUIDE_TAILLES.items()
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — AGENT IA CADEAU "SOFIA"
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec-title">CONSEILLER CADEAU</div>', unsafe_allow_html=True)
st.markdown('<div class="sec-sub">Notre conseillère Sofia vous aide à trouver le hoodie idéal pour un cadeau personnalisé</div>', unsafe_allow_html=True)

# Init agent au premier chargement
if not st.session_state["agent_msgs"]:
    first = AGENT_STEPS[0]
    st.session_state["agent_msgs"] = [{"role": "agent", "text": first["msg"]}]
    st.session_state["agent_step"] = 0

# Affichage chat
st.markdown('<div class="chat-wrap">', unsafe_allow_html=True)
st.markdown("""
<div class="chat-header">
  <div class="agent-av">S</div>
  <div>
    <div class="agent-name">Sofia — Conseillère HoodieWear</div>
    <div class="agent-status">En ligne</div>
  </div>
</div>""", unsafe_allow_html=True)

# Messages
chat_html = '<div class="chat-body">'
for msg in st.session_state["agent_msgs"]:
    cls = "msg-agent" if msg["role"] == "agent" else "msg-user"
    txt = msg["text"].replace("\n", "<br>")
    chat_html += f'<div class="{cls}">{txt}</div>'
chat_html += "</div>"
st.markdown(chat_html, unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Boutons réponses rapides
step_idx  = st.session_state["agent_step"]
is_done   = st.session_state["agent_done"]
cur_step  = AGENT_STEPS[step_idx] if step_idx < len(AGENT_STEPS) else None

if not is_done and cur_step and cur_step.get("quick"):
    quick_cols = st.columns(min(len(cur_step["quick"]), 3))
    for qi, (qc, qtext) in enumerate(zip(quick_cols, cur_step["quick"])):
        with qc:
            st.markdown('<div class="quick-reply-btn">', unsafe_allow_html=True)
            clicked = st.button(qtext, key=f"qb_{step_idx}_{qi}", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            if clicked:
                # Sauvegarder contexte
                if cur_step.get("key"):
                    st.session_state["agent_ctx"][cur_step["key"]] = qtext
                # Ajouter msg utilisateur
                st.session_state["agent_msgs"].append({"role": "user", "text": qtext})
                # Passer à l'étape suivante
                next_idx = step_idx + 1
                st.session_state["agent_step"] = next_idx

                if next_idx < len(AGENT_STEPS):
                    next_step = AGENT_STEPS[next_idx]
                    if next_step["msg"] == "reco":
                        # Générer recommandation
                        reco = agent_generate_reco(st.session_state["agent_ctx"], catalogue)
                        st.session_state["agent_reco"]  = reco
                        st.session_state["agent_done"]  = True
                        st.session_state["agent_msgs"].append({"role": "agent", "text": reco["message"]})
                    else:
                        st.session_state["agent_msgs"].append({"role": "agent", "text": next_step["msg"]})
                st.rerun()

# Saisie libre
if not is_done:
    st.markdown('<div style="padding:0 0 0 0;background:var(--dark2);border-top:1px solid rgba(255,255,255,0.06);border-radius:0 0 14px 14px;padding:12px 16px;">', unsafe_allow_html=True)
    inp_c, btn_c = st.columns([4, 1])
    with inp_c:
        user_input = st.text_input("Répondre à Sofia...", key="agent_input", label_visibility="collapsed")
    with btn_c:
        if st.button("Envoyer", key="agent_send", use_container_width=True):
            if user_input.strip():
                if cur_step and cur_step.get("key"):
                    st.session_state["agent_ctx"][cur_step["key"]] = user_input
                st.session_state["agent_msgs"].append({"role": "user", "text": user_input})
                next_idx = step_idx + 1
                st.session_state["agent_step"] = next_idx
                if next_idx < len(AGENT_STEPS):
                    next_step = AGENT_STEPS[next_idx]
                    if next_step["msg"] == "reco":
                        reco = agent_generate_reco(st.session_state["agent_ctx"], catalogue)
                        st.session_state["agent_reco"]  = reco
                        st.session_state["agent_done"]  = True
                        st.session_state["agent_msgs"].append({"role": "agent", "text": reco["message"]})
                    else:
                        st.session_state["agent_msgs"].append({"role": "agent", "text": next_step["msg"]})
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# Bouton reset
if is_done:
    rc1, rc2 = st.columns([1, 3])
    with rc1:
        if st.button("Recommencer", key="agent_reset", use_container_width=True):
            for k in ["agent_step","agent_ctx","agent_msgs","agent_reco","agent_done"]:
                st.session_state[k] = defaults[k]
            st.rerun()

# Affichage recommandations
if st.session_state.get("agent_reco"):
    reco = st.session_state["agent_reco"]
    st.markdown('<div class="reco-card">', unsafe_allow_html=True)
    occ = st.session_state["agent_ctx"].get("occasion","")
    st.markdown(f'<div class="sec-title" style="font-size:1.3rem;">SELECTION CADEAU{" — " + occ.upper() if occ else ""}</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:0.82rem;color:var(--gray);margin-bottom:16px;">Cliquez sur un modèle pour le charger directement dans le configurateur</div>', unsafe_allow_html=True)

    reco_cols = st.columns(min(len(reco["modeles"]), 3), gap="medium")
    for rc, rh in zip(reco_cols, reco["modeles"]):
        with rc:
            rh_imgs = IMAGES_PAR_MODELE.get(rh.get("image_placeholder","classic"), [""])
            rh_img  = rh_imgs[0] if rh_imgs else ""
            st.markdown(f"""
            <div class="prod-card">
              <img src="{rh_img}" style="width:100%;height:160px;object-fit:cover;object-position:top;display:block;"
                   onerror="this.style.display='none'">
              <div class="prod-info">
                <div class="prod-name" style="font-size:1rem;">{rh['nom']}</div>
                <div class="prod-price" style="font-size:1.1rem;">{rh['prix']} DT</div>
                <div style="font-size:0.72rem;color:var(--gray);margin-top:4px;">{rh['matiere'][:36]}</div>
              </div>
            </div>""", unsafe_allow_html=True)

            if st.button("Configurer ce modèle", key=f"reco_cfg_{rh['id']}", use_container_width=True):
                st.session_state["hoodie_sel"]      = rh
                st.session_state["config_couleur"]  = (
                    reco["couleur_sugg"] if reco["couleur_sugg"] in rh["couleurs_disponibles"]
                    else rh["couleurs_disponibles"][0]
                )
                st.session_state["broder_type"]  = reco["broder_type"]
                st.session_state["broder_texte"] = reco["broder_ex"]
                st.session_state["config_taille"] = (
                    "M" if "M" in rh["tailles_disponibles"] else rh["tailles_disponibles"][0]
                )
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — PANIER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec-title">MON PANIER</div>', unsafe_allow_html=True)

if not st.session_state["panier"]:
    st.markdown("""
    <div style="background:var(--dark2);border-radius:13px;padding:28px;text-align:center;
                color:var(--gray);border:1px solid rgba(255,255,255,0.05);">
      <div style="font-family:Bebas Neue,cursive;font-size:1.3rem;letter-spacing:2px;">PANIER VIDE</div>
      <div style="font-size:0.83rem;margin-top:7px;">Configurez un hoodie ci-dessus pour l'ajouter</div>
    </div>""", unsafe_allow_html=True)
else:
    total = sum(i["prix"] for i in st.session_state["panier"])
    for idx, item in enumerate(st.session_state["panier"]):
        bt_label = broder_labels.get(item.get("broder_type","uni"), "Uni").split("(")[0].strip()
        bt_txt   = f' — {item["broder_texte"]}' if item.get("broder_texte") else ""
        ci1, _, ci3 = st.columns([3, 1, 1])
        with ci1:
            st.markdown(f"""
            <div class="cart-item">
              <div style="display:flex;align-items:center;gap:13px;">
                <div style="width:32px;height:32px;border-radius:50%;background:{item['hex']};
                            border:2px solid rgba(255,255,255,0.15);flex-shrink:0;"></div>
                <div>
                  <div style="font-weight:600;color:white;">{item['nom']}</div>
                  <div style="font-size:0.75rem;color:var(--gray);">
                    {item['couleur'].replace('_',' ').capitalize()} · {bt_label}{bt_txt} · T.{item['taille']}
                  </div>
                </div>
              </div>
              <div style="font-family:'Space Mono',monospace;font-size:1.05rem;
                          color:var(--red);font-weight:700;">{item['prix']} DT</div>
            </div>""", unsafe_allow_html=True)
        with ci3:
            if st.button("Supprimer", key=f"del_{idx}"):
                st.session_state["panier"].pop(idx)
                st.rerun()

    st.markdown(f"""
    <div style="background:var(--dark2);border-radius:11px;padding:18px 22px;margin-top:10px;
                border:1px solid rgba(233,69,96,0.2);">
      <div style="color:var(--gray);font-size:0.80rem;font-family:'Space Mono',monospace;">
        TOTAL ({len(st.session_state['panier'])} article(s))</div>
      <div class="cart-total">{total} DT</div>
      <div style="color:var(--gray);font-size:0.76rem;margin-top:4px;">
        + Livraison 7 DT · Gratuite dès 200 DT</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    o1, o2, o3 = st.columns([2, 1, 1])
    with o1:
        if st.button("Passer la commande", type="primary", use_container_width=True, key="btn_order"):
            st.success("Commande envoyée ! Confirmation par email sous 24h. Livraison 3-5 jours.")
            st.balloons()
            st.session_state["panier"] = []
    with o2:
        if st.button("Vider le panier", use_container_width=True, key="btn_clear"):
            st.session_state["panier"] = []
            st.rerun()
    with o3:
        if st.button("Besoin d'aide", use_container_width=True, key="btn_help"):
            st.switch_page("app.py")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — FAVORIS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec-title">MES FAVORIS</div>', unsafe_allow_html=True)
wish_list = [h for h in catalogue if h["id"] in st.session_state["wishlist"]]

if not wish_list:
    st.markdown("""
    <div style="background:var(--dark2);border-radius:13px;padding:22px;text-align:center;
                color:var(--gray);border:1px solid rgba(255,255,255,0.05);">
      <div style="font-size:0.87rem;">Cliquez sur "Favoris" sur un modèle pour l'ajouter ici</div>
    </div>""", unsafe_allow_html=True)
else:
    w_cols = st.columns(min(len(wish_list), 4), gap="medium")
    for wc, wh in zip(w_cols, wish_list):
        with wc:
            wh_img = (IMAGES_PAR_MODELE.get(wh.get("image_placeholder","classic"), [""]))[0]
            st.markdown(f"""
            <div class="prod-card">
              <img src="{wh_img}" style="width:100%;height:140px;object-fit:cover;
                   object-position:top;display:block;"
                   onerror="this.style.display='none'">
              <div style="padding:9px 12px;">
                <div class="prod-name" style="font-size:0.95rem;">{wh['nom']}</div>
                <div class="prod-price" style="font-size:1rem;">{wh['prix']} DT</div>
              </div>
            </div>""", unsafe_allow_html=True)
            w1, w2 = st.columns(2)
            with w1:
                if st.button("Configurer", key=f"wc_{wh['id']}", use_container_width=True):
                    st.session_state["hoodie_sel"] = wh
                    st.rerun()
            with w2:
                if st.button("Retirer", key=f"wd_{wh['id']}", use_container_width=True):
                    st.session_state["wishlist"].remove(wh["id"])
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div class="hw-footer">
  HOODIEWEAR &copy; 2025 &nbsp;·&nbsp; LIVRAISON TUNISIE 3-5J
  &nbsp;·&nbsp; RETOURS 30J &nbsp;·&nbsp; support@hoodiewear.com
</div>
""", unsafe_allow_html=True)