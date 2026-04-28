import smtplib
import random
import string
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

GMAIL_ADDRESS      = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

# ── Stock temporaire des OTP (en mémoire) ─────────────────────────────────────
# Format : { "email": {"code": "123456", "expires": datetime} }
_otp_store: dict = {}


def _send_email(to_email: str, subject: str, html_body: str) -> bool:
    """Envoie un email via Gmail SMTP"""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"HoodieWear KMS <{GMAIL_ADDRESS}>"
        msg["To"]      = to_email

        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, to_email, msg.as_string())
        return True

    except Exception as e:
        print(f"[Email Error] {e}")
        return False


def _html_template(title: str, content: str) -> str:
    """Template HTML commun pour tous les emails"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,sans-serif;">
        <div style="max-width:520px;margin:40px auto;background:white;
                    border-radius:16px;overflow:hidden;
                    box-shadow:0 4px 24px rgba(0,0,0,0.1);">

            <!-- Header -->
            <div style="background:#e94560;padding:28px;text-align:center;">
                <h1 style="color:white;margin:0;font-size:1.6rem;">👕 HoodieWear</h1>
                <p style="color:rgba(255,255,255,0.85);margin:6px 0 0;font-size:0.9rem;">
                    Smart Knowledge Management System
                </p>
            </div>

            <!-- Body -->
            <div style="padding:32px;">
                <h2 style="color:#222;margin-top:0;">{title}</h2>
                {content}
            </div>

            <!-- Footer -->
            <div style="background:#f9f9f9;padding:16px;text-align:center;
                        border-top:1px solid #eee;">
                <p style="color:#aaa;font-size:0.78rem;margin:0;">
                    © 2025 HoodieWear — Cet email est automatique, ne pas répondre.
                </p>
            </div>
        </div>
    </body>
    </html>
    """


# ── 1. Email de bienvenue ──────────────────────────────────────────────────────
def send_welcome_email(to_email: str, name: str) -> bool:
    content = f"""
    <p style="color:#444;font-size:1rem;">Bonjour <strong>{name}</strong> 👋</p>
    <p style="color:#444;">Bienvenue sur <strong>HoodieWear KMS</strong> !
       Votre compte client a été créé avec succès.</p>

    <div style="background:#f0f9f4;border-left:4px solid #1d9e75;
                padding:16px;border-radius:8px;margin:20px 0;">
        <p style="margin:0;color:#1d9e75;font-weight:bold;">✅ Votre compte est actif</p>
        <p style="margin:6px 0 0;color:#444;font-size:0.9rem;">
            Vous pouvez maintenant vous connecter et accéder à notre assistant IA.
        </p>
    </div>

    <p style="color:#444;">Notre assistant est disponible 24h/24 pour répondre
       à toutes vos questions sur nos produits.</p>

    <p style="color:#888;font-size:0.85rem;margin-top:24px;">
        Email enregistré : <strong>{to_email}</strong>
    </p>
    """
    return _send_email(
        to_email,
        "👕 Bienvenue sur HoodieWear KMS !",
        _html_template("Compte créé avec succès !", content)
    )


# ── 2. OTP à la connexion ──────────────────────────────────────────────────────
def generate_and_send_otp(to_email: str, name: str) -> bool:
    """Génère un code OTP à 6 chiffres et l'envoie par email"""
    code = "".join(random.choices(string.digits, k=6))

    # Stocke avec expiration 10 minutes
    _otp_store[to_email.lower()] = {
        "code":    code,
        "expires": datetime.now() + timedelta(minutes=10)
    }

    content = f"""
    <p style="color:#444;">Bonjour <strong>{name}</strong>,</p>
    <p style="color:#444;">Voici votre code de vérification pour vous connecter :</p>

    <div style="text-align:center;margin:28px 0;">
        <div style="display:inline-block;background:#e94560;color:white;
                    font-size:2.2rem;font-weight:bold;letter-spacing:12px;
                    padding:18px 32px;border-radius:12px;">
            {code}
        </div>
    </div>

    <div style="background:#fff8e1;border-left:4px solid #f0a500;
                padding:14px;border-radius:8px;margin:16px 0;">
        <p style="margin:0;color:#f0a500;font-weight:bold;">⏱️ Code valide 10 minutes</p>
        <p style="margin:6px 0 0;color:#666;font-size:0.88rem;">
            Si vous n'avez pas demandé ce code, ignorez cet email.
        </p>
    </div>
    """
    return _send_email(
        to_email,
        "🔐 Votre code de connexion HoodieWear",
        _html_template("Code de vérification", content)
    )


def verify_otp(email: str, code: str) -> tuple[bool, str]:
    """Vérifie le code OTP"""
    email = email.lower()
    entry = _otp_store.get(email)

    if not entry:
        return False, "Aucun code envoyé pour cet email."
    if datetime.now() > entry["expires"]:
        del _otp_store[email]
        return False, "Code expiré. Demandez-en un nouveau."
    if entry["code"] != code.strip():
        return False, "Code incorrect."

    del _otp_store[email]  # Code à usage unique
    return True, "Code valide !"


# ── 3. Réinitialisation de mot de passe ───────────────────────────────────────
def send_reset_password_otp(to_email: str, name: str) -> bool:
    """Envoie un OTP pour réinitialiser le mot de passe"""
    code = "".join(random.choices(string.digits, k=6))

    _otp_store[f"reset_{to_email.lower()}"] = {
        "code":    code,
        "expires": datetime.now() + timedelta(minutes=15)
    }

    content = f"""
    <p style="color:#444;">Bonjour <strong>{name}</strong>,</p>
    <p style="color:#444;">Vous avez demandé à réinitialiser votre mot de passe.</p>

    <div style="text-align:center;margin:28px 0;">
        <div style="display:inline-block;background:#378add;color:white;
                    font-size:2.2rem;font-weight:bold;letter-spacing:12px;
                    padding:18px 32px;border-radius:12px;">
            {code}
        </div>
    </div>

    <div style="background:#fff8e1;border-left:4px solid #f0a500;
                padding:14px;border-radius:8px;margin:16px 0;">
        <p style="margin:0;color:#f0a500;font-weight:bold;">⏱️ Code valide 15 minutes</p>
        <p style="margin:6px 0 0;color:#666;font-size:0.88rem;">
            Si vous n'avez pas fait cette demande, ignorez cet email.
        </p>
    </div>
    """
    return _send_email(
        to_email,
        "🔑 Réinitialisation de mot de passe HoodieWear",
        _html_template("Réinitialisation de mot de passe", content)
    )


def verify_reset_otp(email: str, code: str) -> tuple[bool, str]:
    """Vérifie l'OTP de reset"""
    key   = f"reset_{email.lower()}"
    entry = _otp_store.get(key)

    if not entry:
        return False, "Aucune demande trouvée."
    if datetime.now() > entry["expires"]:
        del _otp_store[key]
        return False, "Code expiré."
    if entry["code"] != code.strip():
        return False, "Code incorrect."

    del _otp_store[key]
    return True, "Code valide !"