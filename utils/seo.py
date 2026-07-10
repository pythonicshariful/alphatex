"""
utils/seo.py
Auto-generate SEO metadata fields from a Product object.
Called every time a product is created or edited.
"""

import re
import unicodedata


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    """Convert arbitrary text to a URL-safe slug."""
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text).strip('-')
    return text


def _truncate(text: str, max_len: int, suffix: str = '…') -> str:
    """Truncate text to max_len, appending suffix if trimmed."""
    if not text:
        return ''
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[:max_len - len(suffix)].rstrip() + suffix


def _strip_html(text: str) -> str:
    """Remove any HTML tags from a string."""
    if not text:
        return ''
    return re.sub(r'<[^>]+>', '', text).strip()


# ---------------------------------------------------------------------------
# Public generators
# ---------------------------------------------------------------------------

def generate_slug(name: str, product_id: int) -> str:
    """
    Build a unique SEO slug like 'luxury-silk-abaya-42'.
    Always appends the product id to guarantee uniqueness.
    """
    base = _slugify(name)
    if not base:
        base = 'product'
    return f"{base}-{product_id}"


def generate_meta_title(name: str, brand: str = 'Alphatex') -> str:
    """
    Build a <title> tag string.
    Format: "{Product Name} | {Brand}"
    Max 70 characters (Google shows ~60-70).
    """
    full = f"{name.strip()} | {brand}"
    return _truncate(full, 70)


def generate_meta_description(description: str, name: str, category_name: str) -> str:
    """
    Build a compelling <meta name="description"> value.
    Uses actual description text if available, otherwise
    a formula template.  Max 160 characters.
    """
    clean = _strip_html(description or '').replace('\n', ' ')
    clean = re.sub(r'\s+', ' ', clean).strip()

    if clean and len(clean) > 40:
        return _truncate(clean, 160)

    # Fallback template
    fallback = (
        f"Shop {name} at Alphatex — premium {category_name.lower()} "
        f"crafted for the discerning individual. "
        f"Fast delivery · Easy returns."
    )
    return _truncate(fallback, 160)


def generate_meta_keywords(name: str, category_name: str) -> str:
    """
    Build a comma-separated keyword list.
    Combines significant words from name + category + brand terms.
    Max 250 characters.
    """
    stop_words = {
        'a', 'an', 'the', 'of', 'in', 'for', 'and', 'or', 'with', 'at',
        'to', 'by', 'is', 'it', 'on', 'as', 'be', 'this', 'that', 'from'
    }

    def tokenize(text):
        words = re.findall(r'[a-z]+', text.lower())
        return [w for w in words if w not in stop_words and len(w) > 2]

    tokens = tokenize(name) + tokenize(category_name)
    # Deduplicate, preserving order
    seen = set()
    unique = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            unique.append(t)

    # Add brand terms
    brand_terms = ['alphatex', 'luxury', 'premium', 'fashion', category_name.lower()]
    for t in brand_terms:
        if t not in seen:
            seen.add(t)
            unique.append(t)

    result = ', '.join(unique)
    return _truncate(result, 250, suffix='')


# ---------------------------------------------------------------------------
# Master function
# ---------------------------------------------------------------------------

def generate_seo_fields(product, force: bool = False) -> dict:
    """
    Return a dict of all SEO fields for *product*.

    Args:
        product: SQLAlchemy Product instance (must already have .id set).
        force:   If True, regenerate even if fields already exist.

    Returns dict with keys: slug, meta_title, meta_description, meta_keywords
    """
    cat_name = product.category.name if product.category else 'Fashion'

    fields = {}

    # Slug — regenerate always (name may have changed)
    fields['slug'] = generate_slug(product.name, product.id)

    # Meta title
    if force or not product.meta_title:
        fields['meta_title'] = generate_meta_title(product.name)

    # Meta description
    if force or not product.meta_description:
        fields['meta_description'] = generate_meta_description(
            product.description, product.name, cat_name
        )

    # Meta keywords
    if force or not product.meta_keywords:
        fields['meta_keywords'] = generate_meta_keywords(product.name, cat_name)

    return fields


def apply_seo_fields(product, force: bool = False) -> None:
    """
    Convenience wrapper: compute and apply SEO fields directly to the product object.
    Caller is responsible for committing the session.
    """
    fields = generate_seo_fields(product, force=force)
    for key, value in fields.items():
        setattr(product, key, value)
