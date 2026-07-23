"""
bot_protection.py — Multi-layer bot protection middleware for alphatex.
Plugged into Flask as a before_request hook in app.py.
"""
import re
import time
from collections import defaultdict
from flask import request, jsonify, abort, g, session, has_request_context
from functools import lru_cache

# ── Known bot / scanner user-agent patterns ──────────────────────────────────
_BOT_UA_PATTERNS = re.compile(
    r'(sqlmap|nikto|nmap|masscan|zgrab|dirbuster|gobuster|wfuzz|nuclei|'
    r'hydra|metasploit|nessus|openvas|acunetix|burpsuite|w3af|'
    r'python-requests/2\.[0-3]|go-http-client/1|curl/7\.[0-6]|'
    r'libwww-perl|lwp-request|peach|scrapy|mechanize|wget/)',
    re.IGNORECASE,
)

# ── Suspicious request path patterns (scanner probes) ────────────────────────
_SUSPICIOUS_PATHS = re.compile(
    r'(\.\./|\.\.\\|/etc/passwd|/etc/shadow|/proc/self|'
    r'wp-admin|wp-login|phpmyadmin|adminer|\.env|\.git/|'
    r'\.php$|xmlrpc\.php|eval\(|base64_decode|union.*select|'
    r'<script|javascript:|onload=|onerror=)',
    re.IGNORECASE,
)

# ── In-memory failed-request tracker (resets on server restart) ───────────────
# For production use Redis via Flask-Limiter storage instead.
_failed_requests: dict[str, list[float]] = defaultdict(list)
_BLOCK_THRESHOLD   = 20   # failed probes before temp-block
_BLOCK_WINDOW_SEC  = 300  # 5-minute window
_TEMP_BLOCK_SEC    = 600  # 10-minute temp block

# IPs permanently blocked by admin (populated from DB lazily)
_PERM_BLOCKED_IPS: set[str] = set()

def _get_client_ip() -> str:
    """Return real IP, respecting common reverse-proxy headers."""
    for header in ('X-Forwarded-For', 'X-Real-IP', 'CF-Connecting-IP'):
        val = request.headers.get(header)
        if val:
            return val.split(',')[0].strip()
    return request.remote_addr or '0.0.0.0'


def _record_failure(ip: str) -> None:
    now = time.time()
    wins = _failed_requests[ip]
    # prune old entries
    _failed_requests[ip] = [t for t in wins if now - t < _BLOCK_WINDOW_SEC]
    _failed_requests[ip].append(now)


def _is_temp_blocked(ip: str) -> bool:
    now = time.time()
    wins = _failed_requests.get(ip, [])
    # remove stale
    recent = [t for t in wins if now - t < _BLOCK_WINDOW_SEC]
    _failed_requests[ip] = recent
    return len(recent) >= _BLOCK_THRESHOLD


def check_request() -> None:
    """
    Main bot-protection hook. Attach to app.before_request.
    Returns None (allows request) or aborts with 403/400.
    """
    ip = _get_client_ip()
    g.client_ip = ip          # store for use in routes

    # 1. Permanently blocked IPs (admin-set)
    if ip in _PERM_BLOCKED_IPS:
        abort(403)

    # 2. Temporarily blocked IPs (too many scanner probes)
    if _is_temp_blocked(ip):
        abort(429)

    path = request.path
    ua   = request.headers.get('User-Agent', '')

    # 3. Missing User-Agent → almost certainly a bot/script
    if not ua.strip():
        _record_failure(ip)
        abort(403)

    # 4. Known malicious scanner User-Agent
    if _BOT_UA_PATTERNS.search(ua):
        _record_failure(ip)
        abort(403)

    # 5. Suspicious path probing (LFI, SQLi, CMSscan, etc.)
    full = path + '?' + request.query_string.decode('utf-8', 'ignore')
    if _SUSPICIOUS_PATHS.search(full):
        _record_failure(ip)
        abort(403)

    # 6. Excessive query-string length (buffer overflow attempts)
    if len(request.query_string) > 2048:
        _record_failure(ip)
        abort(400)

    # 7. Reject requests with dangerous headers
    for header in ('X-Forwarded-Host', 'X-Host'):
        val = request.headers.get(header, '')
        if val and val != request.host:
            _record_failure(ip)
            abort(400)


def block_ip(ip: str) -> None:
    """Add an IP to the permanent block list (call from admin routes)."""
    _PERM_BLOCKED_IPS.add(ip)


def unblock_ip(ip: str) -> None:
    """Remove an IP from the permanent block list."""
    _PERM_BLOCKED_IPS.discard(ip)


def get_blocked_ips() -> set:
    return set(_PERM_BLOCKED_IPS)


def get_suspicious_ips() -> dict:
    """Return IPs with recent failed attempts, sorted by count descending."""
    now = time.time()
    result = {}
    for ip, times in _failed_requests.items():
        recent = [t for t in times if now - t < _BLOCK_WINDOW_SEC]
        if recent:
            result[ip] = len(recent)
    return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))


def generate_simple_captcha() -> str:
    """Generate simple math captcha question & store answer in session."""
    import random
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    if has_request_context():
        try:
            session['simple_captcha_answer'] = str(num1 + num2)
        except Exception:
            pass
    return f"{num1} + {num2}"


def verify_captcha(response_token=None, form_type='login') -> bool:
    """
    Verifies captcha response token dynamically based on SiteSettings configured in DB.
    Supports Turnstile, Google reCAPTCHA v2 (Checkbox & Invisible), and Simple Math Captcha.
    """
    try:
        from models import SiteSettings
        settings = {s.key: s.value for s in SiteSettings.query.all()}
    except Exception:
        settings = {}

    captcha_enabled = settings.get('captcha_enabled', 'true')
    if captcha_enabled != 'true':
        return True

    # Check form target policy
    if form_type == 'login' and settings.get('captcha_on_login', 'true') != 'true':
        return True
    if form_type == 'register' and settings.get('captcha_on_register', 'true') != 'true':
        return True
    if form_type == 'admin_login' and settings.get('captcha_on_admin_login') != 'true':
        return True

    provider = settings.get('captcha_provider', 'turnstile')
    secret = settings.get('captcha_secret_key') or current_app.config.get('TURNSTILE_SECRET_KEY')

    # Simple Captcha fallback (session-based math answer)
    if provider == 'simple_captcha':
        user_answer = (response_token or request.form.get('simple_captcha_answer') or '').strip()
        expected_answer = str(session.get('simple_captcha_answer', ''))
        session.pop('simple_captcha_answer', None)
        return bool(user_answer and expected_answer and user_answer == expected_answer)

    # If secret key is not set, allow in dev/demo mode
    if not secret:
        return True

    # Extract token from form if not passed directly
    token = response_token or request.form.get('cf-turnstile-response') or request.form.get('g-recaptcha-response')
    if not token:
        return False

    if provider == 'turnstile':
        url = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
        try:
            res = requests.post(url, data={'secret': secret, 'response': token}, timeout=5)
            return res.json().get('success', False)
        except Exception as e:
            current_app.logger.error(f"Turnstile verification error: {e}")
            return False

    elif provider in ('recaptcha_v2', 'recaptcha_v2_invisible'):
        url = 'https://www.google.com/recaptcha/api/siteverify'
        try:
            res = requests.post(url, data={'secret': secret, 'response': token}, timeout=5)
            return res.json().get('success', False)
        except Exception as e:
            current_app.logger.error(f"reCAPTCHA verification error: {e}")
            return False

    return True

