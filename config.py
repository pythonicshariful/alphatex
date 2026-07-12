import os
from dotenv import load_dotenv

load_dotenv()
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'

    # ── Database ─────────────────────────────────────────────────────────────
    # Option A (recommended for Supabase): set individual components so that
    # special characters in the password (@ # % etc.) never break the URL.
    #
    #   DB_HOST     = db.wupyyvkkzmlmyueczahn.supabase.co
    #   DB_PORT     = 5432
    #   DB_NAME     = postgres
    #   DB_USER     = postgres
    #   DB_PASSWORD = <your raw password, no URL-encoding needed>
    #
    # Option B: set DATABASE_URL directly (password must be URL-encoded if it
    # contains special chars — replace @ with %40, # with %23, etc.)
    #
    @classmethod
    def _build_db_uri(cls):
        from urllib.parse import quote_plus
        from sqlalchemy.engine import URL

        # ── Option A: individual env vars (handles any password safely) ──────
        db_host = os.environ.get('DB_HOST')
        if db_host:
            return URL.create(
                drivername='postgresql+psycopg2',
                username=os.environ.get('DB_USER', 'postgres'),
                password=os.environ.get('DB_PASSWORD', ''),
                host=db_host,
                port=int(os.environ.get('DB_PORT', 5432)),
                database=os.environ.get('DB_NAME', 'postgres'),
            )

        # ── Option B: raw DATABASE_URL string ────────────────────────────────
        raw = os.environ.get('DATABASE_URL', '')
        if raw:
            # Fix Heroku/Supabase "postgres://" → "postgresql://"
            if raw.startswith('postgres://'):
                raw = raw.replace('postgres://', 'postgresql://', 1)
            return raw

        # ── Fallback: local SQLite ────────────────────────────────────────────
        return 'sqlite:///' + os.path.join(basedir, 'shop.db')

    SQLALCHEMY_DATABASE_URI = _build_db_uri.__func__(None)
    # ─────────────────────────────────────────────────────────────────────────

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
