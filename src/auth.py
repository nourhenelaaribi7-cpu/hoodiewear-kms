import streamlit as st
import hashlib

USERS = {
    "admin": {
        "password": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": "admin",
        "name": "Administrateur HoodieWear"
    },
    "agent": {
        "password": hashlib.sha256("agent123".encode()).hexdigest(),
        "role": "agent",
        "name": "Agent Service Client"
    },
    "client": {
        "password": hashlib.sha256("client123".encode()).hexdigest(),
        "role": "client",
        "name": "Client HoodieWear"
    }
}

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def check_credentials(username: str, password: str) -> dict | None:
    user = USERS.get(username.lower())
    if user and user["password"] == hash_password(password):
        return {"username": username, "role": user["role"], "name": user["name"]}
    return None

def login_page():
    """Affiche la page de login et gère la session"""
    st.markdown("""
    <style>
    .login-container {
        max-width: 400px;
        margin: 80px auto;
        padding: 40px;
        background: white;
        border-radius: 16px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.1);
        border-top: 4px solid #e94560;
    }
    .login-title {
        text-align: center;
        color: #1a1a2e;
        font-size: 1.8rem;
        margin-bottom: 8px;
    }
    .login-subtitle {
        text-align: center;
        color: #666;
        margin-bottom: 32px;
        font-size: 0.9rem;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="login-container">
        <div class="login-title">👕 HoodieWear KMS</div>
        <div class="login-subtitle">Smart Knowledge Management System</div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        st.subheader("🔐 Connexion")
        username = st.text_input("Nom d'utilisateur", placeholder="admin / agent / client")
        password = st.text_input("Mot de passe", type="password", placeholder="••••••••")
        submit  = st.form_submit_button("Se connecter", use_container_width=True, type="primary")

        if submit:
            user = check_credentials(username, password)
            if user:
                st.session_state.user      = user
                st.session_state.logged_in = True
                st.success(f"✅ Bienvenue {user['name']} !")
                st.rerun()
            else:
                st.error("❌ Identifiants incorrects")

    # Comptes de démonstration
    st.divider()
    st.caption("**Comptes de démonstration :**")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption("👑 Admin\n`admin` / `admin123`")
    with col2:
        st.caption("👨‍💼 Agent\n`agent` / `agent123`")
    with col3:
        st.caption("👤 Client\n`client` / `client123`")

def logout():
    """Déconnecte l'utilisateur"""
    st.session_state.logged_in = False
    st.session_state.user      = None
    st.rerun()

def require_login():
    """À appeler en début de chaque page — redirige vers login si non connecté"""
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        login_page()
        st.stop()
    return st.session_state.user

def require_admin():
    """Bloque l'accès aux non-admins"""
    user = require_login()
    if user["role"] not in ["admin"]:
        st.error("🚫 Accès réservé aux administrateurs.")
        st.info("Connectez-vous avec un compte admin pour accéder à cette page.")
        st.stop()
    return user

def require_agent_or_admin():
    """Réservé aux agents et admins"""
    user = require_login()
    if user["role"] not in ["admin", "agent"]:
        st.error("🚫 Accès réservé aux agents et administrateurs.")
        st.stop()
    return user

def show_user_badge():
    """Affiche le badge utilisateur dans la sidebar"""
    user = st.session_state.get("user", {})
    role = user.get("role", "")
    name = user.get("name", "")

    role_colors = {
        "admin": "#e94560",
        "agent": "#1d9e75",
        "client": "#378add"
    }
    role_icons = {
        "admin": "👑",
        "agent": "👨‍💼",
        "client": "👤"
    }

    color = role_colors.get(role, "#888")
    icon  = role_icons.get(role, "👤")

    st.sidebar.markdown(f"""
    <div style="background:{color}22; border:1px solid {color};
                border-radius:8px; padding:10px; margin-bottom:12px;">
        <div style="color:{color}; font-weight:bold; font-size:0.9rem;">
            {icon} {name}
        </div>
        <div style="color:{color}; font-size:0.78rem; opacity:0.8;">
            Rôle : {role.capitalize()}
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.sidebar.button("🚪 Déconnexion", use_container_width=True):
        logout()