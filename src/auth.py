import json
import os
import hashlib
import streamlit as st
from dotenv import load_dotenv
from datetime import datetime

from src.email_service import (
    send_welcome_email,
    generate_and_send_otp,
    verify_otp,
    send_reset_password_otp,
    verify_reset_otp
)

load_dotenv()

USERS_FILE = "data/users.json"

# ── Comptes staff fixes ────────────────────────────────────────────────────────
INTERNAL_USERS = {
    "admin@hoodiewear.com": {
        "password": hashlib.sha256("admin123".encode()).hexdigest(),
        "role":     "admin",
        "name":     "Administrateur HoodieWear"
    },
    "agent@hoodiewear.com": {
        "password": hashlib.sha256("agent123".encode()).hexdigest(),
        "role":     "agent",
        "name":     "Agent Service Client"
    }
}


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ── Gestion des comptes clients ────────────────────────────────────────────────
def load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else {}
    except Exception:
        return {}


def save_user(email: str, name: str, password: str):
    os.makedirs("data", exist_ok=True)
    users = load_users()
    users[email.lower()] = {
        "name":       name,
        "password":   hash_password(password),
        "role":       "client",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def check_credentials(email: str, password: str) -> dict | None:
    email = email.lower().strip()

    if email in INTERNAL_USERS:
        user = INTERNAL_USERS[email]
        if user["password"] == hash_password(password):
            return {"email": email, "role": user["role"], "name": user["name"]}
        return None

    users = load_users()
    if email in users:
        user = users[email]
        if user["password"] == hash_password(password):
            return {"email": email, "role": "client", "name": user["name"]}

    return None


def register_client(email: str, name: str, password: str) -> tuple[bool, str]:
    email = email.lower().strip()

    if email in INTERNAL_USERS:
        return False, "Cet email est réservé au staff."

    users = load_users()
    if email in users:
        return False, "Un compte existe déjà avec cet email."

    if len(password) < 6:
        return False, "Le mot de passe doit contenir au moins 6 caractères."
    if "@" not in email:
        return False, "Email invalide."
    if len(name.strip()) < 2:
        return False, "Veuillez entrer votre nom complet."

    save_user(email, name, password)

    # ✉️ Email de bienvenue automatique
    send_welcome_email(email, name)

    return True, "Compte créé avec succès !"


# ── Page de login complète ─────────────────────────────────────────────────────
def login_page():
    st.markdown("""
    <style>
    .login-box {
        max-width: 440px; margin: 0 auto; padding: 36px;
        background: white; border-radius: 16px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

    # 3 onglets
    tab1, tab2, tab3 = st.tabs(["🔑 Se connecter", "✨ Créer un compte", "🔓 Mot de passe oublié"])

    # ══════════════════════════════════════════════════════════════════════════
    # ONGLET 1 — Connexion
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        st.markdown("#### Connexion à votre espace HoodieWear")

        # Bouton Google (si configuré)
        google_id = os.getenv("GOOGLE_CLIENT_ID", "")
        if google_id:
            try:
                from streamlit_google_auth import Authenticate
                authenticator = Authenticate(
                    secret_credentials_path=None,
                    cookie_name="hoodiewear_auth",
                    cookie_key="hoodiewear_secret_2025",
                    redirect_uri="http://localhost:8501",
                    client_id=google_id,
                    client_secret=os.getenv("GOOGLE_CLIENT_SECRET", "")
                )
                authenticator.check_authentification()

                if st.session_state.get("connected"):
                    google_user = st.session_state.get("user_info", {})
                    g_email     = google_user.get("email", "")

                    users = load_users()
                    if g_email and g_email not in users and g_email not in INTERNAL_USERS:
                        save_user(
                            g_email,
                            google_user.get("name", "Client Google"),
                            "google_oauth_no_password"
                        )

                    st.session_state.user = {
                        "email":   g_email,
                        "name":    google_user.get("name", "Client"),
                        "role":    INTERNAL_USERS.get(g_email, {}).get("role", "client"),
                        "picture": google_user.get("picture", "")
                    }
                    st.session_state.logged_in = True
                    st.rerun()

                st.markdown("**Connexion rapide :**")
                authenticator.login()
                st.markdown("---")
                st.caption("ou avec email/mot de passe :")

            except Exception:
                pass

        # ── Étape 1 : Email + Mot de passe ────────────────────────────────────
        if not st.session_state.get("otp_step"):
            with st.form("form_login"):
                email    = st.text_input("📧 Email", placeholder="votre@email.com")
                password = st.text_input("🔒 Mot de passe", type="password")
                submit   = st.form_submit_button(
                    "Se connecter →", use_container_width=True, type="primary"
                )

                if submit:
                    if not email or not password:
                        st.error("Veuillez remplir tous les champs.")
                    else:
                        user = check_credentials(email, password)
                        if user:
                            if user["role"] == "client":
                                # 🔐 OTP pour les clients uniquement
                                ok = generate_and_send_otp(email, user["name"])
                                if ok:
                                    st.session_state["pending_user"] = user
                                    st.session_state["otp_step"]     = True
                                    st.success("📧 Code envoyé sur votre email !")
                                    st.rerun()
                                else:
                                    st.error("❌ Erreur d'envoi email. Vérifiez votre configuration Gmail.")
                            else:
                                # Admin/Agent → connexion directe sans OTP
                                st.session_state.user      = user
                                st.session_state.logged_in = True
                                st.rerun()
                        else:
                            st.error("❌ Email ou mot de passe incorrect.")

        # ── Étape 2 : Vérification OTP ────────────────────────────────────────
        else:
            pending_email = st.session_state.get("pending_user", {}).get("email", "")
            st.info(f"📧 Code envoyé à : **{pending_email}**")
            st.markdown("#### 🔐 Vérification en deux étapes")
            st.caption("Entrez le code à 6 chiffres reçu par email (valide 10 min).")

            with st.form("form_otp"):
                otp_code = st.text_input(
                    "Code OTP", placeholder="123456",
                    max_chars=6
                )
                col1, col2 = st.columns(2)
                with col1:
                    verify = st.form_submit_button(
                        "✅ Vérifier", use_container_width=True, type="primary"
                    )
                with col2:
                    resend = st.form_submit_button(
                        "🔄 Renvoyer le code", use_container_width=True
                    )

                if verify:
                    pending = st.session_state.get("pending_user", {})
                    ok, msg = verify_otp(pending.get("email", ""), otp_code)
                    if ok:
                        st.session_state.user      = pending
                        st.session_state.logged_in = True
                        st.session_state.otp_step  = False
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")

                if resend:
                    pending = st.session_state.get("pending_user", {})
                    generate_and_send_otp(pending["email"], pending["name"])
                    st.success("📧 Nouveau code envoyé !")

            # Bouton pour annuler et revenir au formulaire
            if st.button("← Retour", use_container_width=False):
                st.session_state["otp_step"]    = False
                st.session_state["pending_user"] = None
                st.rerun()

        # Comptes démo
        with st.expander("🎯 Comptes de démonstration"):
            st.caption("👑 Admin : `admin@hoodiewear.com` / `admin123`")
            st.caption("👨‍💼 Agent : `agent@hoodiewear.com` / `agent123`")
            st.caption("👤 Client : créez un compte dans l'onglet 'Créer un compte'")

    # ══════════════════════════════════════════════════════════════════════════
    # ONGLET 2 — Inscription
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("#### Créer votre compte client HoodieWear")
        st.caption("Accédez à l'assistant IA pour toutes vos questions.")

        with st.form("form_register"):
            col1, col2 = st.columns(2)
            with col1:
                prenom = st.text_input("Prénom", placeholder="Ahmed")
            with col2:
                nom = st.text_input("Nom", placeholder="Bacha")

            email     = st.text_input("📧 Email", placeholder="ahmed@gmail.com")
            password  = st.text_input(
                "🔒 Mot de passe", type="password", help="Minimum 6 caractères"
            )
            password2 = st.text_input("🔒 Confirmer le mot de passe", type="password")
            accept    = st.checkbox("J'accepte les conditions d'utilisation de HoodieWear")

            submit_reg = st.form_submit_button(
                "Créer mon compte →", use_container_width=True, type="primary"
            )

            if submit_reg:
                if not all([prenom, nom, email, password, password2]):
                    st.error("❌ Veuillez remplir tous les champs.")
                elif password != password2:
                    st.error("❌ Les mots de passe ne correspondent pas.")
                elif not accept:
                    st.warning("⚠️ Veuillez accepter les conditions d'utilisation.")
                else:
                    full_name = f"{prenom.strip()} {nom.strip()}"
                    success, message = register_client(email, full_name, password)

                    if success:
                        st.success(f"✅ {message}")
                        st.info("📧 Un email de bienvenue vous a été envoyé !")
                        st.info("Connectez-vous dans l'onglet 'Se connecter'.")
                        st.balloons()
                    else:
                        st.error(f"❌ {message}")

    # ══════════════════════════════════════════════════════════════════════════
    # ONGLET 3 — Mot de passe oublié
    # ══════════════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("#### 🔓 Réinitialiser votre mot de passe")

        step = st.session_state.get("reset_step", 1)

        # ── Étape 1 : Saisie de l'email ───────────────────────────────────────
        if step == 1:
            st.caption("Entrez votre email pour recevoir un code de réinitialisation.")

            with st.form("form_reset_1"):
                email  = st.text_input("📧 Votre email", placeholder="votre@email.com")
                submit = st.form_submit_button(
                    "Envoyer le code →", use_container_width=True, type="primary"
                )

                if submit:
                    email = email.lower().strip()
                    users = load_users()

                    if email in users:
                        name = users[email]["name"]
                        send_reset_password_otp(email, name)
                        st.session_state["reset_email"] = email
                        st.session_state["reset_step"]  = 2
                        st.success("📧 Code envoyé sur votre email !")
                        st.rerun()
                    elif email in INTERNAL_USERS:
                        st.error("❌ Les comptes staff ne peuvent pas réinitialiser leur mot de passe ici.")
                    else:
                        st.error("❌ Aucun compte trouvé avec cet email.")

        # ── Étape 2 : Code OTP + nouveau mot de passe ─────────────────────────
        elif step == 2:
            reset_email = st.session_state.get("reset_email", "")
            st.info(f"📧 Code envoyé à : **{reset_email}**")
            st.caption("Entrez le code reçu et choisissez un nouveau mot de passe (valide 15 min).")

            with st.form("form_reset_2"):
                code      = st.text_input("🔐 Code reçu par email", placeholder="123456", max_chars=6)
                new_pass  = st.text_input("🔒 Nouveau mot de passe", type="password")
                new_pass2 = st.text_input("🔒 Confirmer le mot de passe", type="password")
                submit    = st.form_submit_button(
                    "Réinitialiser →", use_container_width=True, type="primary"
                )

                if submit:
                    if not all([code, new_pass, new_pass2]):
                        st.error("❌ Veuillez remplir tous les champs.")
                    elif new_pass != new_pass2:
                        st.error("❌ Les mots de passe ne correspondent pas.")
                    elif len(new_pass) < 6:
                        st.error("❌ Minimum 6 caractères.")
                    else:
                        ok, msg = verify_reset_otp(reset_email, code)
                        if not ok:
                            st.error(f"❌ {msg}")
                        else:
                            # ✅ Sauvegarde le nouveau mot de passe
                            users = load_users()
                            users[reset_email]["password"] = hash_password(new_pass)
                            with open(USERS_FILE, "w", encoding="utf-8") as f:
                                json.dump(users, f, ensure_ascii=False, indent=2)

                            st.session_state["reset_step"] = 1
                            st.success("✅ Mot de passe mis à jour avec succès !")
                            st.info("Connectez-vous avec votre nouveau mot de passe.")
                            st.balloons()
                            st.rerun()

            if st.button("← Retour", key="reset_back"):
                st.session_state["reset_step"] = 1
                st.rerun()


# ── Fonctions de protection des pages ─────────────────────────────────────────
def logout():
    st.session_state.logged_in = False
    st.session_state.user      = None
    st.session_state.otp_step  = False
    st.session_state.reset_step = 1
    if "connected" in st.session_state:
        st.session_state.connected = False
    st.rerun()


def require_login():
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        login_page()
        st.stop()
    return st.session_state.user


def require_admin():
    user = require_login()
    if user["role"] != "admin":
        st.error("🚫 Accès réservé aux administrateurs.")
        st.stop()
    return user


def require_agent_or_admin():
    user = require_login()
    if user["role"] not in ["admin", "agent"]:
        st.error("🚫 Accès réservé aux agents et administrateurs.")
        st.stop()
    return user


def show_user_badge():
    user    = st.session_state.get("user", {})
    role    = user.get("role", "")
    name    = user.get("name", "")
    picture = user.get("picture", "")

    role_colors = {"admin": "#e94560", "agent": "#1d9e75", "client": "#378add"}
    role_icons  = {"admin": "👑",       "agent": "👨‍💼",       "client": "👤"}
    role_labels = {"admin": "Administrateur", "agent": "Agent", "client": "Client"}

    color = role_colors.get(role, "#888")
    icon  = role_icons.get(role, "👤")
    label = role_labels.get(role, role)

    if picture:
        st.sidebar.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;
                    background:{color}22;border:1px solid {color};
                    border-radius:8px;padding:8px 12px;margin-bottom:12px;">
            <img src="{picture}" width="36" height="36"
                 style="border-radius:50%;border:2px solid {color}">
            <div>
                <div style="color:{color};font-weight:bold;font-size:0.85rem;">
                    {icon} {name}
                </div>
                <div style="color:{color};font-size:0.75rem;opacity:0.8;">
                    {label}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.sidebar.markdown(f"""
        <div style="background:{color}22;border:1px solid {color};
                    border-radius:8px;padding:10px;margin-bottom:12px;">
            <div style="color:{color};font-weight:bold;font-size:0.9rem;">
                {icon} {name}
            </div>
            <div style="color:{color};font-size:0.78rem;opacity:0.8;">
                {label}
            </div>
        </div>
        """, unsafe_allow_html=True)

    if st.sidebar.button("🚪 Déconnexion", use_container_width=True):
        logout()