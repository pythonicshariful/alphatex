"""
migrate_seo.py — works with SQLite (local) and PostgreSQL (Supabase)
Run ONCE to add SEO columns and back-fill all existing products.

Usage:
    python migrate_seo.py
"""

import os
import sys
import re
import unicodedata
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get('DATABASE_URL', '')

# ── Detect backend ────────────────────────────────────────────────────────────
USE_POSTGRES = DB_URL.startswith('postgres://') or DB_URL.startswith('postgresql://')

if USE_POSTGRES:
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        print("ERROR: psycopg2-binary not installed. Run: pip install psycopg2-binary")
        sys.exit(1)
else:
    import sqlite3
    DB_PATH = os.path.join(os.path.dirname(__file__), 'shop.db')
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}")
        sys.exit(1)

# ── Inline SEO helpers ────────────────────────────────────────────────────────

def _slugify(text):
    text = unicodedata.normalize('NFKD', str(text))
    text = text.encode('ascii', 'ignore').decode('ascii').lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    return re.sub(r'[\s_-]+', '-', text).strip('-')

def _truncate(text, max_len, suffix='…'):
    if not text: return ''
    text = text.strip()
    return text if len(text) <= max_len else text[:max_len - len(suffix)].rstrip() + suffix

def _strip_html(text):
    return re.sub(r'<[^>]+>', '', str(text or '')).strip()

def generate_slug(name, product_id):
    return f"{_slugify(name) or 'product'}-{product_id}"

def generate_meta_title(name):
    return _truncate(f"{name.strip()} | Alphatex", 70)

def generate_meta_description(description, name, category_name):
    clean = re.sub(r'\s+', ' ', _strip_html(description)).strip()
    if clean and len(clean) > 40:
        return _truncate(clean, 160)
    return _truncate(
        f"Shop {name} at Alphatex — premium {category_name.lower()} "
        f"crafted for the discerning individual. Fast delivery · Easy returns.", 160)

def generate_meta_keywords(name, category_name):
    stop = {'a','an','the','of','in','for','and','or','with','at','to','by','is','it','on'}
    def tokenize(t):
        return [w for w in re.findall(r'[a-z]+', t.lower()) if w not in stop and len(w) > 2]
    tokens = tokenize(name) + tokenize(category_name)
    seen, unique = set(), []
    for t in tokens:
        if t not in seen: seen.add(t); unique.append(t)
    for t in ['alphatex', 'luxury', 'premium', 'fashion', category_name.lower()]:
        if t not in seen: seen.add(t); unique.append(t)
    return _truncate(', '.join(unique), 250, suffix='')

# ── Database helpers ──────────────────────────────────────────────────────────

if USE_POSTGRES:
    conn = psycopg2.connect(DB_URL.replace('postgres://', 'postgresql://'))
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    PH   = '%s'   # PostgreSQL placeholder

    # Check columns via information_schema
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'product'
    """)
    existing_cols = {row['column_name'] for row in cur.fetchall()}

    new_cols = [
        ("slug",             "VARCHAR(220)"),
        ("meta_title",       "VARCHAR(70)"),
        ("meta_description", "VARCHAR(160)"),
        ("meta_keywords",    "VARCHAR(250)"),
    ]
    added = []
    for col_name, col_type in new_cols:
        if col_name not in existing_cols:
            cur.execute(f"ALTER TABLE product ADD COLUMN IF NOT EXISTS {col_name} {col_type}")
            added.append(col_name)
            print(f"  [+] Added column: {col_name}")

else:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur  = conn.cursor()
    PH   = '?'    # SQLite placeholder

    cur.execute("PRAGMA table_info(product)")
    existing_cols = {row['name'] for row in cur.fetchall()}

    new_cols = [("slug","TEXT"),("meta_title","TEXT"),("meta_description","TEXT"),("meta_keywords","TEXT")]
    added = []
    for col_name, col_type in new_cols:
        if col_name not in existing_cols:
            cur.execute(f"ALTER TABLE product ADD COLUMN {col_name} {col_type}")
            added.append(col_name)
            print(f"  [+] Added column: {col_name}")

if added:
    conn.commit()
    print(f"\n  ✓ Schema updated: {', '.join(added)}")
else:
    print("  ✓ All SEO columns already exist — skipping schema change.")

# ── Back-fill all products ────────────────────────────────────────────────────

cur.execute(
    "SELECT p.id, p.name, p.description, c.name as cat_name "
    "FROM product p LEFT JOIN category c ON p.category_id = c.id"
)
products = cur.fetchall()
updated  = 0

for p in products:
    pid      = p['id']
    name     = p['name'] or ''
    desc     = p['description'] or ''
    cat_name = p['cat_name'] or 'Fashion'

    slug       = generate_slug(name, pid)
    meta_title = generate_meta_title(name)
    meta_desc  = generate_meta_description(desc, name, cat_name)
    meta_kw    = generate_meta_keywords(name, cat_name)

    cur.execute(
        f"UPDATE product SET slug={PH}, meta_title={PH}, meta_description={PH}, meta_keywords={PH} WHERE id={PH}",
        (slug, meta_title, meta_desc, meta_kw, pid)
    )
    updated += 1
    print(f"  [{pid}] {name[:40]!r}  →  {slug}")

conn.commit()
conn.close()
print(f"\n  ✓ SEO fields generated for {updated} product(s).")
print(f"\nDone! Backend: {'PostgreSQL (Supabase)' if USE_POSTGRES else 'SQLite'}")
