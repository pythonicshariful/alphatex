import os
from dotenv import load_dotenv

load_dotenv()
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'shop.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 30 * 24 * 60 * 60  # 30 days for customers

    # Admin session is shorter (handled per-route)
    ADMIN_SESSION_TIMEOUT = 30 * 60  # 30 minutes

    # SMTP Settings
    SMTP_SERVER = os.environ.get('SMTP_SERVER') or 'alphatex.bd'
    SMTP_PORT = int(os.environ.get('SMTP_PORT') or 465)
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME') or 'no-reply@alphatex.bd'
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD') or 'Hacktanha@24'

    # Admin brute force
    ADMIN_MAX_FAILED_ATTEMPTS = 5
    ADMIN_LOCKOUT_MINUTES = 30

    # IP whitelist (empty = disabled)
    ADMIN_ALLOWED_IPS = [ip.strip() for ip in (os.environ.get('ADMIN_ALLOWED_IPS') or '').split(',') if ip.strip()]

    # OAuth Credentials
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    FACEBOOK_CLIENT_ID = os.environ.get('FACEBOOK_CLIENT_ID')
    FACEBOOK_CLIENT_SECRET = os.environ.get('FACEBOOK_CLIENT_SECRET')
