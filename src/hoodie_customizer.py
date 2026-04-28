
"""
HoodieWear — Utilitaires catalogue, tailles, SVG ultra-réaliste

"""
import os, json, base64
from pathlib import Path

# ── Racine projet ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent          
ASSETS = ROOT / "data" / "images"                     
CATALOGUE_FILE = ROOT / "data" / "raw" / "catalogue_hoodies.json"

# ── Palette couleurs ───────────────────────────────────────────────────────────
COULEURS_CSS = {
    "noir": "#1a1a1a", "blanc": "#f5f5f0", "gris": "#9e9e9e",
    "gris_clair": "#d0d0d0", "marine": "#1a237e", "bleu": "#1565c0",
    "bleu_ciel": "#29b6f6", "rouge": "#c62828", "bordeaux": "#6d1b1b",
    "rose": "#f48fb1", "rose_pale": "#fce4ec", "vert": "#2e7d32",
    "vert_olive": "#827717", "kaki": "#5d4037", "beige": "#d7ccc8",
    "camel": "#a0785a", "orange": "#e65100", "jaune": "#f9a825",
    "violet": "#4a148c", "lilas": "#ce93d8", "marron": "#4e2112",
}

GUIDE_TAILLES = {
    "XS":  {"poitrine": "80-85",   "epaules": "38-39", "longueur": "63"},
    "S":   {"poitrine": "86-91",   "epaules": "40-41", "longueur": "65"},
    "M":   {"poitrine": "92-97",   "epaules": "42-43", "longueur": "68"},
    "L":   {"poitrine": "98-103",  "epaules": "44-45", "longueur": "71"},
    "XL":  {"poitrine": "104-109", "epaules": "46-47", "longueur": "74"},
    "XXL": {"poitrine": "110-116", "epaules": "48-50", "longueur": "77"},
}

# ── Chargement images locales → base64 data URI ───────────────────────────────
def _img_b64(path: Path) -> str:
    """Lit une image et retourne un data URI base64 (PNG)."""
    if not path.exists():
        return ""
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()

def get_images_modele(modele: str) -> list[str]:
    """
    Retourne la liste des data URIs base64 pour un modele.
    Cherche dans  data/images/{modele}/{modele}_1.png ... {modele}_5.png
    Si le dossier n'existe pas, utilise  data/images/classic/  comme fallback.
    """
    folder = ASSETS / modele
    nom    = modele          # prefixe des fichiers dans ce dossier

    if not folder.exists():
        folder = ASSETS / "classic"
        nom    = "classic"   # les fichiers s'appellent classic_1.png etc.

    imgs = []
    for i in range(1, 6):
        p = folder / f"{nom}_{i}.png"
        if not p.exists():
            # dernier recours : classic
            p = ASSETS / "classic" / f"classic_{i}.png"
        b = _img_b64(p)
        if b:
            imgs.append(b)
    return imgs if imgs else [""]

# Dictionnaire global chargé une seule fois au démarrage
def build_images_dict() -> dict:
    result = {}
    for modele in ["classic", "oversized", "zip", "crop", "premium"]:
        imgs = get_images_modele(modele)
        result[modele] = imgs
    return result

def debug_images_paths() -> str:
    """Retourne un résumé des images trouvées pour debug dans Streamlit."""
    lines = [f"ASSETS = {ASSETS}", f"Exists: {ASSETS.exists()}"]
    for modele in ["classic", "oversized", "zip", "crop", "premium"]:
        folder = ASSETS / modele
        imgs = get_images_modele(modele)
        lines.append(f"{modele}: folder={'OK' if folder.exists() else 'MISSING'}, images={len(imgs)}")
    return "\n".join(lines)

IMAGES_PAR_MODELE: dict = {}   # rempli par build_images_dict() dans la page

def ensure_images_loaded():
    global IMAGES_PAR_MODELE
    if not IMAGES_PAR_MODELE:
        IMAGES_PAR_MODELE = build_images_dict()

IMAGES_HOODIES: dict = {}  # première image de chaque modèle

# ── Images personnalisation (exemples broderie) ───────────────────────────────
def get_perso_examples() -> list[str]:
    """Retourne les 4 images d'exemple de personnalisation."""
    folder = ASSETS / "perso"
    imgs = []
    for i in range(1, 5):
        p = folder / f"perso_{i}.png"
        b = _img_b64(p)
        if b:
            imgs.append(b)
    return imgs


# ══════════════════════════════════════════════════════════════════════════════
# CATALOGUE
# ══════════════════════════════════════════════════════════════════════════════

def _catalogue_defaut() -> list:
    return [
        {
            "id": "hw_classic_001", "nom": "Classic Hoodie",
            "description": "Notre hoodie intemporel, coupe regular confortable pour toutes les occasions.",
            "prix": 79, "matiere": "80% coton, 20% polyester",
            "rating": 4.6, "avis": 312, "nouveaute": False,
            "image_placeholder": "classic",
            "couleurs_disponibles": ["noir", "blanc", "gris", "marine", "rouge", "bordeaux"],
            "designs_disponibles": ["uni", "logo_poitrine", "broderie_poitrine", "texte_personnalise"],
            "tailles_disponibles": ["XS", "S", "M", "L", "XL", "XXL"],
        },
        {
            "id": "hw_oversized_002", "nom": "Oversized Hoodie",
            "description": "Coupe oversize tendance, parfait pour un look streetwear décontracté.",
            "prix": 99, "matiere": "85% coton bio, 15% polyester recyclé",
            "rating": 4.9, "avis": 218, "nouveaute": True,
            "image_placeholder": "oversized",
            "couleurs_disponibles": ["noir", "gris", "beige", "bleu_ciel", "rose_pale", "lilas", "camel"],
            "designs_disponibles": ["uni", "logo_poitrine", "print_poitrine", "broderie_poitrine",
                                    "bandes_laterales", "texte_personnalise"],
            "tailles_disponibles": ["S", "M", "L", "XL", "XXL"],
        },
        {
            "id": "hw_zip_003", "nom": "Zip Hoodie",
            "description": "Hoodie zippé polyvalent, idéal pour les demi-saisons.",
            "prix": 109, "matiere": "75% coton, 25% polyester recyclé",
            "rating": 4.7, "avis": 156, "nouveaute": True,
            "image_placeholder": "zip",
            "couleurs_disponibles": ["noir", "marine", "gris", "bordeaux", "vert", "kaki", "bleu", "marron"],
            "designs_disponibles": ["uni", "logo_poitrine", "logo_dos", "bandes_laterales", "texte_personnalise"],
            "tailles_disponibles": ["XS", "S", "M", "L", "XL", "XXL"],
        },
        {
            "id": "hw_crop_004", "nom": "Crop Hoodie",
            "description": "Version crop tendance, parfaite pour un style sporty-chic affirmé.",
            "prix": 89, "matiere": "80% coton, 20% polyester",
            "rating": 4.5, "avis": 94, "nouveaute": False,
            "image_placeholder": "crop",
            "couleurs_disponibles": ["blanc", "rose", "beige", "lilas", "bleu_ciel", "rose_pale"],
            "designs_disponibles": ["uni", "broderie_poitrine", "print_poitrine", "texte_personnalise"],
            "tailles_disponibles": ["XS", "S", "M", "L"],
        },
        {
            "id": "hw_premium_005", "nom": "Premium Hoodie",
            "description": "Notre modèle haut de gamme, tissu 450g/m² et finitions luxueuses.",
            "prix": 149, "matiere": "100% coton peigné 450g/m²",
            "rating": 5.0, "avis": 67, "nouveaute": True,
            "image_placeholder": "premium",
            "couleurs_disponibles": ["noir", "marine", "bordeaux", "camel", "vert_olive", "gris", "marron"],
            "designs_disponibles": ["uni", "broderie_poitrine", "broderie_dos", "logo_poitrine",
                                    "print_dos", "texte_personnalise"],
            "tailles_disponibles": ["S", "M", "L", "XL", "XXL"],
        },
    ]


def load_catalogue() -> list:
    if not CATALOGUE_FILE.exists():
        return _catalogue_defaut()
    try:
        with open(CATALOGUE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if data else _catalogue_defaut()
    except Exception:
        return _catalogue_defaut()


def get_hoodies_similaires(hoodie_id: str, catalogue: list) -> list:
    current = next((h for h in catalogue if h["id"] == hoodie_id), None)
    if not current:
        return []
    return [h for h in catalogue
            if h["id"] != hoodie_id and abs(h["prix"] - current["prix"]) <= 35][:2]


# ══════════════════════════════════════════════════════════════════════════════
# TAILLES
# ══════════════════════════════════════════════════════════════════════════════

def recommander_taille(taille_cm, poids_kg, tour_poitrine=None, style_prefere="regular"):
    imc = poids_kg / ((taille_cm / 100) ** 2)
    if not tour_poitrine:
        factor = 0.48 if imc < 18.5 else 0.52 if imc < 25 else 0.56 if imc < 30 else 0.60
        tour_poitrine = int(taille_cm * factor)

    taille_base = "M"
    for t, m in GUIDE_TAILLES.items():
        mn, mx = map(int, m["poitrine"].split("-"))
        if mn <= tour_poitrine <= mx:
            taille_base = t
            break

    ordre = ["XS", "S", "M", "L", "XL", "XXL"]
    idx   = ordre.index(taille_base)

    if style_prefere == "oversized" and idx < len(ordre) - 1:
        taille_finale = ordre[idx + 1]
        note = "Pour un style oversized, on monte d'une taille."
    elif style_prefere == "fitted" and idx > 0:
        taille_finale = ordre[idx - 1]
        note = "Pour un style fitted, on descend d'une taille."
    else:
        taille_finale = taille_base
        note = "Taille standard recommandée pour votre morphologie."

    alts = []
    if idx > 0:            alts.append(ordre[idx - 1])
    if idx < len(ordre)-1: alts.append(ordre[idx + 1])

    return {
        "taille": taille_finale, "taille_base": taille_base, "alternatives": alts,
        "tour_poitrine": tour_poitrine, "imc": round(imc, 1),
        "mesures": GUIDE_TAILLES[taille_finale], "note_style": note,
        "explication": (
            f"Avec {taille_cm}cm et {poids_kg}kg (IMC {round(imc,1)}), "
            f"tour de poitrine estimé à ~{tour_poitrine}cm. {note}"
        ),
    }


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS COULEUR
# ══════════════════════════════════════════════════════════════════════════════

def _hex_to_rgb(h: str):
    h = h.lstrip("#")
    return int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)

def _lighten(h: str, f: float = 0.22) -> str:
    r,g,b = _hex_to_rgb(h)
    return "#{:02x}{:02x}{:02x}".format(
        min(255,int(r+(255-r)*f)), min(255,int(g+(255-g)*f)), min(255,int(b+(255-b)*f)))

def _darken(h: str, f: float = 0.28) -> str:
    r,g,b = _hex_to_rgb(h)
    return "#{:02x}{:02x}{:02x}".format(int(r*(1-f)), int(g*(1-f)), int(b*(1-f)))


# ══════════════════════════════════════════════════════════════════════════════
# SVG HOODIE ULTRA-RÉALISTE v5
# Nouveautés : broderie initiales géantes, prénom, date sur manche, logo HW
# ══════════════════════════════════════════════════════════════════════════════

def generer_apercu_svg(
    couleur: str = "noir",
    design: str = "uni",
    texte: str = "",
    modele: str = "classic",
    broder_type: str = "uni",   # uni | initiales | prenom | date | texte | logo
    broder_texte: str = "",
    broder_font: str = "serif", # serif | block | script
) -> str:
    fill  = COULEURS_CSS.get(couleur, "#1a1a1a")
    r,g,b = _hex_to_rgb(fill)
    lum   = (0.299*r + 0.587*g + 0.114*b) / 255
    isDark = lum < 0.45

    detail  = "rgba(255,255,255,0.88)" if isDark else "rgba(0,0,0,0.70)"
    lhi     = _lighten(fill, 0.20)
    mid     = _darken(fill,  0.14)
    drk     = _darken(fill,  0.32)
    acc     = "#e94560"
    isZip   = modele == "zip"
    isCrop  = modele == "crop"
    bot     = 252 if isCrop else 298

    fonts = {
        "serif":  "Georgia,'Times New Roman',serif",
        "block":  "'Arial Black',Impact,sans-serif",
        "script": "cursive,Georgia,serif",
    }
    ff    = fonts.get(broder_font, fonts["serif"])
    fstyle = "italic" if broder_font == "script" else "normal"
    fweight = "900"   if broder_font == "block"  else "400"

    svg = f"""<svg viewBox="0 0 320 380" xmlns="http://www.w3.org/2000/svg"
     style="max-width:100%;height:auto;display:block;margin:auto;filter:drop-shadow(0 18px 36px rgba(0,0,0,0.20));">
  <defs>
    <linearGradient id="gb" x1="0.1" y1="0" x2="0.9" y2="1">
      <stop offset="0%"   stop-color="{lhi}"/>
      <stop offset="45%"  stop-color="{fill}"/>
      <stop offset="100%" stop-color="{drk}"/>
    </linearGradient>
    <linearGradient id="gsl" x1="1" y1="0" x2="0" y2="0.7">
      <stop offset="0%"   stop-color="{fill}"/>
      <stop offset="100%" stop-color="{drk}"/>
    </linearGradient>
    <linearGradient id="gsr" x1="0" y1="0" x2="1" y2="0.7">
      <stop offset="0%"   stop-color="{fill}"/>
      <stop offset="100%" stop-color="{drk}"/>
    </linearGradient>
    <linearGradient id="gh" x1="0.2" y1="0" x2="0.8" y2="1">
      <stop offset="0%"   stop-color="{lhi}"/>
      <stop offset="55%"  stop-color="{fill}"/>
      <stop offset="100%" stop-color="{mid}"/>
    </linearGradient>
    <radialGradient id="ghi" cx="50%" cy="45%" r="55%">
      <stop offset="0%"   stop-color="{drk}" stop-opacity="0.55"/>
      <stop offset="100%" stop-color="{drk}" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <!-- Ombre sol -->
  <ellipse cx="160" cy="372" rx="86" ry="7" fill="rgba(0,0,0,0.14)"/>

  <!-- MANCHE GAUCHE -->
  <path d="M58 120 C38 125 14 138 8 172 C3 196 8 222 13 238 L46 233
           C41 218 36 194 42 172 C48 152 62 136 76 128 Z" fill="url(#gsl)"/>
  <path d="M58 120 C62 132 66 145 70 158 C68 145 65 130 76 128 Z"
        fill="{drk}" opacity="0.42"/>
  <path d="M13 238 C11 246 14 253 22 254 L48 249 C54 248 56 242 54 236 Z" fill="{fill}"/>
  <path d="M10 240 C8 249 13 256 22 257 L50 252 C57 251 59 244 56 238"
        fill="none" stroke="{detail}" stroke-width="1.3" stroke-opacity="0.25" stroke-linecap="round"/>

  <!-- MANCHE DROITE -->
  <path d="M262 120 C282 125 306 138 312 172 C317 196 312 222 307 238 L274 233
           C279 218 284 194 278 172 C272 152 258 136 244 128 Z" fill="url(#gsr)"/>
  <path d="M262 120 C258 132 254 145 250 158 C252 145 255 130 244 128 Z"
        fill="{drk}" opacity="0.42"/>
  <path d="M308 238 C310 246 307 253 298 254 L272 249 C266 248 264 242 266 236 Z" fill="{fill}"/>
  <path d="M310 240 C312 249 307 256 298 257 L270 252 C263 251 261 244 264 238"
        fill="none" stroke="{detail}" stroke-width="1.3" stroke-opacity="0.25" stroke-linecap="round"/>

  <!-- CORPS -->
  <path d="M78 130 L58 120 L65 86 L92 58 L228 58 L255 86 L262 120 L242 130 L240 {bot} L80 {bot} Z"
        fill="url(#gb)"/>
  <!-- Reflet épaule gauche -->
  <path d="M65 86 L92 58 L112 58 C98 70 84 85 78 130 L65 86 Z" fill="{lhi}" opacity="0.10"/>
  <!-- Ombres latérales corps -->
  <path d="M78 130 L80 {bot} L95 {bot} L95 140 Z" fill="{drk}" opacity="0.17"/>
  <path d="M242 130 L240 {bot} L225 {bot} L225 140 Z" fill="{drk}" opacity="0.17"/>
  <!-- Ceinture bas -->
  <rect x="80" y="{bot-2}" width="160" height="13" rx="5" fill="{drk}" opacity="0.36"/>
  <line x1="80" y1="{bot+5}" x2="240" y2="{bot+5}"
        stroke="{detail}" stroke-width="0.7" stroke-opacity="0.20"/>
"""

    # ── CAPUCHE ────────────────────────────────────────────────────────────────
    if isZip:
        zip_teeth = "".join([
            f'<rect x="155" y="{68+i*8}" width="10" height="3" rx="1" '
            f'fill="{lhi if isDark else mid}" opacity="0.32"/>'
            for i in range(min(28, (bot-68)//8))
        ])
        svg += f"""
  <!-- CAPUCHE ZIP -->
  <path d="M92 58 C90 22 100 4 160 2 C220 4 230 22 228 58
           L212 74 C204 44 186 32 160 30 C134 32 116 44 108 74 Z" fill="url(#gh)"/>
  <path d="M108 74 C116 44 134 32 160 30 C186 32 204 44 212 74" fill="url(#ghi)"/>
  <!-- ZIP -->
  <rect x="157" y="56" width="6" height="{bot-56}" rx="3" fill="{drk}" opacity="0.48"/>
  <line x1="160" y1="56" x2="160" y2="{bot}"
        stroke="{detail}" stroke-width="1.4" stroke-opacity="0.28"/>
  {zip_teeth}
  <!-- Curseur zip -->
  <rect x="151" y="93" width="18" height="14" rx="4"
        fill="{mid}" stroke="{detail}" stroke-width="0.8" stroke-opacity="0.3"/>
  <rect x="154" y="96" width="12" height="8" rx="2" fill="{drk}" opacity="0.52"/>
  <circle cx="160" cy="100" r="2.2" fill="{detail}" opacity="0.48"/>
"""
    else:
        svg += f"""
  <!-- CAPUCHE CLASSIQUE -->
  <path d="M94 58 C92 20 103 2 160 0 C217 2 228 20 226 58
           L210 76 C202 46 184 35 160 33 C136 35 118 46 110 76 Z" fill="url(#gh)"/>
  <path d="M110 76 C118 46 136 35 160 33 C184 35 202 46 210 76" fill="url(#ghi)"/>
  <!-- Rebord intérieur -->
  <path d="M110 76 C118 46 136 35 160 33 C184 35 202 46 210 76"
        fill="none" stroke="{detail}" stroke-width="2.4" stroke-opacity="0.28" stroke-linecap="round"/>
  <!-- Couture centrale capuche -->
  <path d="M160 0 C160 10 160 22 160 33"
        fill="none" stroke="{detail}" stroke-width="1" stroke-opacity="0.10" stroke-dasharray="3,2"/>
  <!-- Cordons -->
  <line x1="132" y1="76" x2="124" y2="220"
        stroke="{detail}" stroke-width="2.4" stroke-opacity="0.25" stroke-linecap="round"/>
  <line x1="188" y1="76" x2="196" y2="220"
        stroke="{detail}" stroke-width="2.4" stroke-opacity="0.25" stroke-linecap="round"/>
  <ellipse cx="124" cy="222" rx="5" ry="3.5" fill="{detail}" opacity="0.42"/>
  <ellipse cx="196" cy="222" rx="5" ry="3.5" fill="{detail}" opacity="0.42"/>
"""

    # ── POCHE KANGOUROU ────────────────────────────────────────────────────────
    if not isCrop:
        svg += f"""
  <!-- POCHE KANGOUROU -->
  <path d="M112 228 C110 264 124 276 160 277 C196 276 210 264 208 228
           L203 225 C203 260 190 270 160 271 C130 270 117 260 117 225 Z"
        fill="{mid}"/>
  <path d="M112 228 C116 224 136 222 160 222 C184 222 204 224 208 228"
        fill="none" stroke="{detail}" stroke-width="1.1" stroke-opacity="0.22" stroke-dasharray="3,2"/>
  <line x1="160" y1="222" x2="160" y2="271"
        stroke="{detail}" stroke-width="0.9" stroke-opacity="0.14" stroke-dasharray="2,2"/>
"""

    # ── BRODERIE / PERSONNALISATION ────────────────────────────────────────────
    cy = 162  # centre Y zone broderie

    if broder_type == "logo":
        svg += f"""
  <!-- Logo HW brodé -->
  <circle cx="160" cy="{cy}" r="26" fill="{acc}" opacity="0.93"/>
  <circle cx="160" cy="{cy}" r="22" fill="none"
          stroke="rgba(255,255,255,0.28)" stroke-width="1.5"/>
  <text x="160" y="{cy+6}" text-anchor="middle" font-size="15"
        font-family="Arial Black,Impact,sans-serif" font-weight="900"
        fill="white" letter-spacing="2">HW</text>"""

    elif broder_type == "initiales" and broder_texte:
        t = broder_texte.upper()[:2]
        fs = 60 if len(t) == 1 else 44
        svg += f"""
  <!-- Initiales géantes brodées -->
  <text x="160" y="{cy + fs//3}" text-anchor="middle" font-size="{fs}"
        font-family="{ff}" font-weight="{fweight}" font-style="{fstyle}"
        fill="{acc}" opacity="0.92">{t}</text>"""

    elif broder_type == "prenom" and broder_texte:
        t = broder_texte[:14]
        fs = 22 if len(t) <= 6 else 17 if len(t) <= 10 else 14
        svg += f"""
  <!-- Prénom brodé -->
  <text x="160" y="{cy+6}" text-anchor="middle" font-size="{fs}"
        font-family="{ff}" font-weight="{fweight}" font-style="{fstyle}"
        fill="{acc}" opacity="0.92">{t}</text>
  <line x1="{160-len(t)*4}" y1="{cy+13}" x2="{160+len(t)*4}" y2="{cy+13}"
        stroke="{acc}" stroke-width="0.9" opacity="0.45"/>"""

    elif broder_type == "date" and broder_texte:
        t = broder_texte[:14]
        svg += f"""
  <!-- Date brodée sur la manche gauche -->
  <g transform="rotate(-90 50 175)">
    <text x="50" y="175" text-anchor="middle" font-size="11"
          font-family="{ff}" font-weight="{fweight}" font-style="{fstyle}"
          fill="{acc}" opacity="0.88">{t}</text>
  </g>
  <!-- Coeur brodé poitrine -->
  <path d="M152,{cy-10} C152,{cy-16} 144,{cy-18} 144,{cy-10}
           C144,{cy-4} 152,{cy+4} 160,{cy+12}
           C168,{cy+4} 176,{cy-4} 176,{cy-10}
           C176,{cy-18} 168,{cy-16} 168,{cy-10}
           C168,{cy-14} 160,{cy-12} 160,{cy-6} Z"
        fill="{acc}" opacity="0.85"/>"""

    elif broder_type == "texte" and broder_texte:
        t = broder_texte[:16]
        fs = 18 if len(t) <= 8 else 15 if len(t) <= 12 else 12
        svg += f"""
  <!-- Texte brodé libre -->
  <text x="160" y="{cy+5}" text-anchor="middle" font-size="{fs}"
        font-family="{ff}" font-weight="{fweight}" font-style="{fstyle}"
        fill="{acc}" opacity="0.92" letter-spacing="2">{t}</text>
  <line x1="{160-len(t)*3.5}" y1="{cy+12}" x2="{160+len(t)*3.5}" y2="{cy+12}"
        stroke="{acc}" stroke-width="0.8" opacity="0.40"/>"""

    # Designs catalogue classiques (compatibilité ancienne)
    elif design == "logo_poitrine":
        svg += f"""
  <circle cx="160" cy="{cy}" r="24" fill="{acc}" opacity="0.93"/>
  <text x="160" y="{cy+6}" text-anchor="middle" font-size="14"
        font-family="Arial Black,sans-serif" font-weight="900"
        fill="white" letter-spacing="2">HW</text>"""

    elif design == "broderie_poitrine":
        svg += f"""
  <text x="160" y="{cy-2}" text-anchor="middle" font-size="13"
        font-family="Georgia,serif" fill="{acc}" font-style="italic" opacity="0.92">HoodieWear</text>
  <line x1="114" y1="{cy+6}" x2="206" y2="{cy+6}"
        stroke="{acc}" stroke-width="1.1" opacity="0.55"/>"""

    elif design == "bandes_laterales":
        svg += f"""
  <rect x="80" y="128" width="10" height="{bot-130}" rx="5" fill="{acc}" opacity="0.80"/>
  <rect x="230" y="128" width="10" height="{bot-130}" rx="5" fill="{acc}" opacity="0.80"/>
  <line x1="56" y1="124" x2="28" y2="210"
        stroke="{acc}" stroke-width="9" stroke-linecap="round" opacity="0.72"/>
  <line x1="264" y1="124" x2="292" y2="210"
        stroke="{acc}" stroke-width="9" stroke-linecap="round" opacity="0.72"/>"""

    elif design == "texte_personnalise" and texte:
        t = texte[:14]
        svg += f"""
  <text x="160" y="{cy+5}" text-anchor="middle" font-size="15"
        font-family="Arial Black,Impact,sans-serif" font-weight="900"
        fill="{detail}" fill-opacity="0.85" letter-spacing="3">{t}</text>"""

    # Badge nouveauté
    if modele in ("oversized", "zip", "premium"):
        svg += f"""
  <rect x="196" y="42" width="76" height="22" rx="11" fill="{acc}"/>
  <text x="234" y="57" text-anchor="middle" font-size="9"
        font-family="Arial Black,sans-serif" font-weight="900"
        fill="white" letter-spacing="1.5">NOUVEAU</text>"""

    svg += "\n</svg>"
    return svg


# ══════════════════════════════════════════════════════════════════════════════
# AGENT IA CADEAU — logique de conversation
# ══════════════════════════════════════════════════════════════════════════════

AGENT_STEPS = [
    {
        "id": "start",
        "msg": "Bonjour ! Je suis Sofia, votre conseillère HoodieWear.\nJe vous aide à trouver le cadeau parfait.\n\nPour quelle occasion cherchez-vous ?",
        "quick": ["Saint Valentin", "Anniversaire", "Fête des Mères", "Noël", "Juste comme ça"],
        "key": None,
    },
    {
        "id": "genre",
        "msg": "Parfait ! C'est un cadeau pour une femme ou un homme ?",
        "quick": ["Une femme", "Un homme", "Non binaire / unisexe"],
        "key": "occasion",
    },
    {
        "id": "couleur",
        "msg": "Quelle est sa couleur préférée, ou son style général ?",
        "quick": ["Couleurs sombres (noir, marine, bordeaux)", "Couleurs douces (beige, rose, lilas)",
                  "Couleurs vives (rouge, bleu vif)", "Je ne sais pas"],
        "key": "genre",
    },
    {
        "id": "style",
        "msg": "Comment décririez-vous son style au quotidien ?",
        "quick": ["Discret et élégant", "Streetwear et décontracté",
                  "Sport et dynamique", "Cosy et confort avant tout"],
        "key": "couleur",
    },
    {
        "id": "perso",
        "msg": "Souhaitez-vous ajouter une personnalisation brodée ? C'est ce qui rend le cadeau vraiment unique !",
        "quick": ["Ses initiales brodées", "Son prénom brodé", "Une date spéciale",
                  "Un texte personnalisé", "Non, je préfère uni"],
        "key": "style",
    },
    {
        "id": "budget",
        "msg": "Quel est votre budget pour ce cadeau ?",
        "quick": ["Moins de 90 DT", "Entre 90 et 120 DT", "Plus de 120 DT — le meilleur pour lui/elle"],
        "key": "perso",
    },
    {
        "id": "reco",
        "msg": "reco",
        "quick": [],
        "key": "budget",
    },
]

def agent_generate_reco(context: dict, catalogue: list) -> dict:
    """
    Génère la recommandation finale de l'agent en fonction du contexte.
    Retourne un dict : { message, modeles: [...], couleur_suggeree, broder_type, broder_ex }
    """
    occ    = context.get("occasion", "")
    genre  = context.get("genre", "")
    couleur= context.get("couleur", "")
    style  = context.get("style", "")
    perso  = context.get("perso", "")
    budget = context.get("budget", "")

    # Déterminer couleur suggérée
    if "doux" in couleur or "rose" in couleur or "lilas" in couleur:
        coul_sugg = "rose" if "femme" in genre.lower() else "lilas"
    elif "vive" in couleur or "rouge" in couleur:
        coul_sugg = "rouge"
    elif "sombre" in couleur or "noir" in couleur:
        coul_sugg = "marine" if "élégant" in style.lower() else "noir"
    else:
        coul_sugg = "noir" if "homme" in genre.lower() else "marine"

    # Déterminer type broderie
    broder_type = "uni"
    broder_ex   = ""
    broder_hint = ""
    if "initiales" in perso.lower():
        broder_type = "initiales"
        broder_ex   = "A.B"
        broder_hint = "Remplacez A.B par ses vraies initiales dans le configurateur"
    elif "prénom" in perso.lower():
        broder_type = "prenom"
        broder_ex   = "Sarah" if "femme" in genre.lower() else "Adam"
        broder_hint = "Entrez son prénom dans le configurateur"
    elif "date" in perso.lower():
        broder_type = "date"
        broder_ex   = "14.02.2025" if "valentin" in occ.lower() else "01.01.2025"
        broder_hint = "Une date qui a de la signification — anniversaire, rencontre..."
    elif "texte" in perso.lower():
        broder_type = "texte"
        broder_ex   = "MON AMOUR" if "valentin" in occ.lower() else "POUR TOI"
        broder_hint = "Personnalisez le texte dans le configurateur"

    # Filtrer catalogue par budget
    if "Moins" in budget:
        recos = [h for h in catalogue if h["prix"] < 90]
    elif "90" in budget:
        recos = [h for h in catalogue if 90 <= h["prix"] <= 120]
    else:
        recos = [h for h in catalogue if h["prix"] >= 109]
    if not recos:
        recos = catalogue[:3]
    recos = recos[:3]

    # Message personnalisé
    occ_str = f" pour {occ}" if occ else ""
    broder_str = f"avec **{perso.lower()}**" if broder_type != "uni" else "uni (sobre et élégant)"
    msg = (
        f"Voici mes recommandations{occ_str} ! "
        f"J'ai sélectionné {len(recos)} modèle(s) parfaitement adaptés.\n\n"
        f"En coloris **{coul_sugg}**, {broder_str} — "
        f"c'est une attention qui marquera les esprits. "
    )
    if broder_hint:
        msg += f"\n\nConseil : {broder_hint}."

    return {
        "message":       msg,
        "modeles":       recos,
        "couleur_sugg":  coul_sugg,
        "broder_type":   broder_type,
        "broder_ex":     broder_ex,
    }


# ══════════════════════════════════════════════════════════════════════════════
# RECOMMANDATION IA (Groq / LLM externe)
# ══════════════════════════════════════════════════════════════════════════════

def generer_recommendation_ia(profil: dict, preferences: dict, catalogue: list) -> str:
    try:
        from groq import Groq
        from dotenv import load_dotenv
        load_dotenv()
        _client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    except Exception as e:
        return f"Client IA indisponible : {e}"

    budget   = preferences.get("budget_max", 999)
    filtered = [h for h in catalogue if h["prix"] <= budget]
    cat_txt  = "\n".join([
        f"- {h['nom']} ({h['prix']} DT) : {h['description'][:80]}"
        f" | Couleurs : {', '.join(h['couleurs_disponibles'][:4])}"
        for h in filtered[:5]
    ])
    prompt = (
        f"Tu es conseiller expert chez HoodieWear (Tunisie).\n"
        f"Profil : {profil.get('taille_cm')}cm / {profil.get('poids_kg')}kg, "
        f"style {profil.get('style_prefere')}.\n"
        f"Préférences : couleur {preferences.get('couleur')}, "
        f"design {preferences.get('design')}, budget {budget} DT.\n"
        f"Catalogue :\n{cat_txt}\n"
        f"Donne 3 phrases max : modèle recommandé + pourquoi, astuce style, alternative. "
        f"En français, ton chaleureux."
    )
    try:
        r = _client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5, max_tokens=280
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        return f"Assistant temporairement indisponible. ({e})"