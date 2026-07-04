"""
bot_protection.py — Multi-layer bot protection middleware for alphatex.
Plugged into Flask as a before_request hook in app.py.
"""
import re
import time
from collections import defaultdict
from flask import request, jsonify, abort, g
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
