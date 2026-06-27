# utils.py
"""Utility helpers for authentication, OTP, email, and activity logging.
All functions are deliberately small and stateless so they can be imported
anywhere inside the Flask app.
"""
import os
import secrets
import datetime
from flask import current_app, session, request
from flask_mail import Message
from werkzeug.security import generate_password_hash, check_password_hash
from .. import mail  # Flask-Mail instance initialized in app/__init__.py
from .models import query_db, execute_db  # helper wrappers around MySQLdb cursor

# ---------------------------------------------------------------------------
# Password handling
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Return a salted hash using Werkzeug's default (pbkdf2:sha256)."""
    return generate_password_hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Check a plaintext password against a stored hash."""
    return check_password_hash(hashed, password)

# ---------------------------------------------------------------------------
# OTP generation and storage
# ---------------------------------------------------------------------------

def generate_otp() -> str:
    """Generate a 6‑digit numeric OTP as a zero‑padded string.
    Uses `secrets.randbelow` for cryptographic randomness.
    """
    return f"{secrets.randbelow(900000) + 100000:06d}"


def store_otp(user_id: int, otp: str, purpose: str, expiry_minutes: int = 5) -> None:
    """Insert OTP into `email_otps` table.
    Parameters
    ----------
    user_id: int – PK of the user the OTP belongs to.
    otp: str – 6‑digit string.
    purpose: str – one of 'registration', 'password_reset', '2fa'.
    expiry_minutes: int – validity window (default 5).
    """
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=expiry_minutes)
    sql = (
        "INSERT INTO email_otps (user_id, otp, purpose, expires_at) "
        "VALUES (%s, %s, %s, %s)"
    )
    execute_db(sql, (user_id, otp, purpose, expires_at))


def verify_otp(user_id: int, otp: str, purpose: str) -> bool:
    """Validate OTP – returns True only if it matches, is not expired and not used.
    The row is marked used atomically to prevent replay attacks.
    """
    conn = query_db(
        "SELECT id, expires_at, used FROM email_otps "
        "WHERE user_id=%s AND otp=%s AND purpose=%s",
        (user_id, otp, purpose),
        one=True,
    )
    if not conn:
        return False
    if conn['used']:
        return False
    if conn['expires_at'] < datetime.datetime.utcnow():
        return False
    # Mark as used
    execute_db(
        "UPDATE email_otps SET used=TRUE WHERE id=%s",
        (conn['id'],),
    )
    return True

# ---------------------------------------------------------------------------
# Email sending (Flask‑Mail)
# ---------------------------------------------------------------------------

def send_otp_email(recipient: str, otp: str, purpose: str) -> None:
    """Send an email containing the OTP.
    The subject differs per purpose to give the user context.
    """
    subject_map = {
        'registration': 'Your Registration OTP',
        'password_reset': 'Password Reset OTP',
        '2fa': 'Your Two‑Factor Authentication OTP',
    }
    subject = subject_map.get(purpose, 'Your OTP')
    body = (
        f"Hello,\n\nYour OTP for {purpose.replace('_', ' ')} is: {otp}\n"
        "It will expire in 5 minutes.\n\nIf you did not request this, please ignore this email."
    )
    msg = Message(subject=subject, recipients=[recipient], body=body)
    mail.send(msg)

# ---------------------------------------------------------------------------
# Activity logging
# ---------------------------------------------------------------------------

def log_activity(user_id: int, role: str, action: str) -> None:
    """Insert a row into `activity_logs`.
    IP address is obtained from the request context.
    """
    ip = request.remote_addr or '0.0.0.0'
    sql = (
        "INSERT INTO activity_logs (user_id, role, action, ip_address) "
        "VALUES (%s, %s, %s, %s)"
    )
    execute_db(sql, (user_id, role, action, ip))
"""End of utils.py"""
