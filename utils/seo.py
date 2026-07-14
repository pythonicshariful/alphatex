"""
utils/seo.py
Auto-generate high-quality SEO metadata fields from a Product object.
Called every time a product is created or edited, and on first-view back-fill.

Optimised for:
  - Google / Bing / AI-powered search (E-E-A-T compliant)
  - Bangladesh luxury fashion market (alphatex.bd)
  - 50-60 char titles, 150-160 char descriptions, 10-20 long-tail keywords
"""

import re
import unicodedata


# ---------------------------------------------------------------------------
# Category-specific long-tail keyword maps
# ---------------------------------------------------------------------------

CATEGORY_KEYWORDS = {
    'men': [
        'mens fashion Bangladesh',
        'buy panjabi online Bangladesh',
        'luxury thobe Bangladesh',
        'premium kurta set men',
        'mens ethnic wear BD',
        'designer menswear Dhaka',
        'traditional mens clothing Bangladesh',
        'formal mens outfit BD',
        'buy thobe online Bangladesh',
        'premium mens fashion Alphatex',
    ],
    'women': [
        'ladies fashion Bangladesh',
        'buy abaya online Bangladesh',
        'hijab collection Bangladesh',
        'luxury womenswear BD',
        'designer abaya Dhaka',
        'premium ladies clothing Bangladesh',
        'modest fashion Bangladesh',
        'women ethnic wear BD',
        'buy maxi dress online BD',
        'premium women fashion Alphatex',
    ],
    'accessories': [
        'leather wallet Bangladesh',
        'mens accessories BD',
        'luxury watch Bangladesh',
        'premium belt online BD',
        'oud fragrance Bangladesh',
        'buy leather accessories Bangladesh',
        'designer accessories Dhaka',
        'luxury fragrance BD',
        'premium accessories Alphatex',
        'mens fashion accessories Bangladesh',
    ],
}

# Per-product override data for rich, hand-crafted SEO metadata
PRODUCT_SEO_OVERRIDES = {
    'Signature Platinum Thobe': {
        'title': 'Signature Platinum Thobe for Men | Alphatex',
        'description': (
            'Shop the Signature Platinum Thobe at Alphatex — handcrafted luxury menswear '
            'for the discerning gentleman. Premium fabric, exquisite stitching. Free delivery in Bangladesh.'
        ),
        'keywords': [
            'signature platinum thobe', 'luxury thobe men', 'premium thobe Bangladesh',
            'buy thobe online BD', 'mens thobe Dhaka', 'traditional thobe men',
            'designer thobe Bangladesh', 'Alphatex thobe', 'formal thobe menswear',
            'high quality thobe BD',
        ],
    },
    'Luxury Silk Abaya': {
        'title': 'Luxury Silk Abaya for Women | Alphatex Bangladesh',
        'description': (
            'Discover the Luxury Silk Abaya at Alphatex — flowing premium silk, elegant design, '
            'perfect for modern modest fashion. Shop online with fast delivery across Bangladesh.'
        ),
        'keywords': [
            'luxury silk abaya', 'premium abaya Bangladesh', 'buy silk abaya online BD',
            'elegant abaya women', 'modest fashion abaya', 'designer abaya Dhaka',
            'Alphatex abaya', 'silk abaya collection', 'ladies abaya Bangladesh',
            'best abaya online Bangladesh',
        ],
    },
    'Classic Leather Wallet': {
        'title': 'Classic Genuine Leather Wallet | Alphatex Accessories',
        'description': (
            'The Alphatex Classic Leather Wallet — crafted from genuine leather for durability and '
            'style. A perfect gift or everyday essential. Shop premium accessories in Bangladesh.'
        ),
        'keywords': [
            'genuine leather wallet Bangladesh', 'mens leather wallet BD', 'buy wallet online Bangladesh',
            'premium wallet Dhaka', 'classic wallet men', 'Alphatex leather wallet',
            'designer wallet Bangladesh', 'slim leather wallet', 'quality wallet BD',
            'leather accessories Bangladesh',
        ],
    },
    'Sahara Linen Panjabi': {
        'title': 'Sahara Linen Panjabi — Premium Menswear | Alphatex',
        'description': (
            'The Sahara Linen Panjabi from Alphatex features breathable linen fabric and refined '
            'craftsmanship. Ideal for Eid, weddings and formal events. Fast delivery across Bangladesh.'
        ),
        'keywords': [
            'linen panjabi Bangladesh', 'sahara linen panjabi', 'buy panjabi online BD',
            'premium panjabi men', 'Eid panjabi Alphatex', 'linen ethnic wear men',
            'designer panjabi Dhaka', 'formal panjabi Bangladesh', 'wedding panjabi BD',
            'best panjabi online Bangladesh',
        ],
    },
    'Premium Co-Ord Set': {
        'title': 'Premium Women\'s Co-Ord Set | Alphatex Fashion',
        'description': (
            'Shop the Premium Co-Ord Set for women at Alphatex — perfectly matched top and bottom '
            'in luxurious fabric. Effortless elegance for every occasion. Free delivery in Bangladesh.'
        ),
        'keywords': [
            'premium co-ord set women', 'ladies co-ord set Bangladesh', 'matching set women BD',
            'buy co-ord set online Bangladesh', 'luxury women outfit Dhaka', 'Alphatex co-ord set',
            'designer matching set women', 'womens two piece set BD', 'elegant outfit women Bangladesh',
            'co-ord fashion Bangladesh',
        ],
    },
    'Oud Fragrance Collection': {
        'title': 'Oud Fragrance Collection — Luxury Scents | Alphatex',
        'description': (
            'Immerse yourself in Alphatex\'s Oud Fragrance Collection — rich, deep Middle Eastern '
            'scents crafted for lasting impression. Premium luxury fragrance available across Bangladesh.'
        ),
        'keywords': [
            'oud fragrance Bangladesh', 'luxury oud perfume BD', 'buy oud online Bangladesh',
            'premium oud fragrance Dhaka', 'Arabic oud perfume BD', 'Alphatex oud collection',
            'best oud perfume Bangladesh', 'oud attar BD', 'luxury scent Bangladesh',
            'Middle Eastern fragrance BD',
        ],
    },
    'Embroidered Kurta Set': {
        'title': 'Embroidered Kurta Set for Men | Alphatex',
        'description': (
            'The Alphatex Embroidered Kurta Set combines intricate hand-embroidery with premium '
            'fabric for a regal look. Perfect for Eid and weddings. Shop menswear online in Bangladesh.'
        ),
        'keywords': [
            'embroidered kurta set men', 'premium kurta set Bangladesh', 'buy kurta set online BD',
            'Eid kurta men Alphatex', 'wedding kurta Bangladesh', 'designer kurta Dhaka',
            'luxury kurta set BD', 'hand embroidered kurta', 'ethnic kurta men Bangladesh',
            'formal kurta set BD',
        ],
    },
    'Designer Hijab Collection': {
        'title': 'Designer Hijab Collection — Modest Fashion | Alphatex',
        'description': (
            'Elevate your modest style with Alphatex\'s Designer Hijab Collection — premium fabrics, '
            'beautiful colours, designed for elegance. Free delivery on orders over ৳2000 in Bangladesh.'
        ),
        'keywords': [
            'designer hijab Bangladesh', 'premium hijab collection BD', 'buy hijab online Bangladesh',
            'modest fashion hijab Dhaka', 'luxury hijab women', 'Alphatex hijab collection',
            'stylish hijab BD', 'quality hijab Bangladesh', 'hijab modest fashion BD',
            'ladies hijab collection Bangladesh',
        ],
    },
    'Premium Leather Belt': {
        'title': 'Premium Leather Belt — Men\'s Accessories | Alphatex',
        'description': (
            'Shop the Alphatex Premium Leather Belt — genuine leather, precision buckle, built to last. '
            'The ideal men\'s accessory for formal and casual wear. Fast delivery across Bangladesh.'
        ),
        'keywords': [
            'premium leather belt men', 'genuine leather belt Bangladesh', 'buy belt online BD',
            'mens belt Dhaka', 'Alphatex leather belt', 'formal belt men Bangladesh',
            'designer belt BD', 'quality leather belt', 'mens accessories belt Bangladesh',
            'luxury belt BD',
        ],
    },
    'Classic White Panjabi': {
        'title': 'Classic White Panjabi for Men | Alphatex Bangladesh',
        'description': (
            'The Alphatex Classic White Panjabi — timeless design, crisp premium fabric, perfect for '
            'prayer, Eid and formal occasions. Order online with fast delivery across Bangladesh.'
        ),
        'keywords': [
            'white panjabi men Bangladesh', 'classic panjabi BD', 'buy white panjabi online',
            'premium panjabi Eid Bangladesh', 'formal white panjabi Dhaka', 'Alphatex white panjabi',
            'traditional panjabi men BD', 'prayer panjabi Bangladesh', 'white ethnic wear men',
            'best panjabi BD',
        ],
    },
    'Elegant Maxi Dress': {
        'title': 'Elegant Maxi Dress for Women | Alphatex Fashion',
        'description': (
            'Shop the Alphatex Elegant Maxi Dress — floor-length luxury, flowing silhouette perfect '
            'for parties, weddings and formal events. Free delivery on orders over ৳2000 in Bangladesh.'
        ),
        'keywords': [
            'elegant maxi dress women', 'luxury maxi dress Bangladesh', 'buy maxi dress online BD',
            'womens long dress Dhaka', 'formal dress women Bangladesh', 'Alphatex maxi dress',
            'designer long dress BD', 'party dress women Bangladesh', 'wedding maxi dress BD',
            'premium dress women Bangladesh',
        ],
    },
    'Premium Watch': {
        'title': 'Premium Luxury Watch — Alphatex Accessories',
        'description': (
            'Discover the Alphatex Premium Watch — sophisticated design, precision movement, '
            'crafted for those who define luxury. Shop premium watches online with delivery across Bangladesh.'
        ),
        'keywords': [
            'premium watch Bangladesh', 'luxury watch BD', 'buy watch online Bangladesh',
            'mens watch Dhaka', 'Alphatex premium watch', 'designer watch Bangladesh',
            'quality watch BD', 'fashion watch men Bangladesh', 'wristwatch Bangladesh',
            'luxury accessories watch BD',
        ],
    },
}


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
    Build a unique SEO slug like 'luxury-silk-abaya-2'.
    Always appends the product id to guarantee DB uniqueness.
    Format: {keyword-rich-name}-{id}
    """
    base = _slugify(name)
    if not base:
        base = 'product'
    return f"{base}-{product_id}"


def generate_meta_title(name: str, brand: str = 'Alphatex',
                        category_name: str = '') -> str:
    """
    Build a <title> tag string optimised for 50-60 characters.
    Uses per-product override when available; falls back to template.
    """
    override = PRODUCT_SEO_OVERRIDES.get(name)
    if override:
        return _truncate(override['title'], 70)

    # Formula: "{Product Name} | {Brand}"
    full = f"{name.strip()} | {brand}"
    return _truncate(full, 70)


def generate_meta_description(description: str, name: str,
                               category_name: str) -> str:
    """
    Build a compelling <meta name="description"> value.
    Uses per-product override when available.
    150-160 characters, includes CTA, primary keyword, value proposition.
    """
    override = PRODUCT_SEO_OVERRIDES.get(name)
    if override:
        return _truncate(override['description'], 160)

    clean = _strip_html(description or '').replace('\n', ' ')
    clean = re.sub(r'\s+', ' ', clean).strip()

    if clean and len(clean) > 50:
        # Append CTA if there is room
        cta = ' Fast delivery · Easy returns across Bangladesh.'
        combined = clean + cta
        return _truncate(combined, 160)

    # Fallback template with strong CTA
    fallback = (
        f"Shop {name} at Alphatex — premium {category_name.lower()} "
        f"crafted for the discerning individual. "
        f"Fast delivery across Bangladesh. Easy returns guaranteed."
    )
    return _truncate(fallback, 160)


def generate_meta_keywords(name: str, category_name: str,
                            category_id: str = '') -> str:
    """
    Build a comma-separated keyword list with 10-20 long-tail terms.
    Max 250 characters.
    """
    override = PRODUCT_SEO_OVERRIDES.get(name)
    if override:
        keywords = override['keywords']
        # Append global brand terms
        brand_terms = ['Alphatex', 'luxury fashion Bangladesh', 'premium fashion BD']
        all_kw = keywords + [t for t in brand_terms if t.lower() not in
                             [k.lower() for k in keywords]]
        return _truncate(', '.join(all_kw), 250, suffix='')

    # Fallback: tokenise + category long-tails
    stop_words = {
        'a', 'an', 'the', 'of', 'in', 'for', 'and', 'or', 'with', 'at',
        'to', 'by', 'is', 'it', 'on', 'as', 'be', 'this', 'that', 'from'
    }

    def tokenize(text):
        words = re.findall(r'[a-z]+', text.lower())
        return [w for w in words if w not in stop_words and len(w) > 2]

    tokens = tokenize(name) + tokenize(category_name)
    seen = set()
    unique = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            unique.append(t)

    # Add category-specific long-tail keywords
    cat_key = category_id.lower() if category_id else category_name.lower().split()[0]
    extra = CATEGORY_KEYWORDS.get(cat_key, [])
    for term in extra[:8]:
        if term.lower() not in seen:
            seen.add(term.lower())
            unique.append(term)

    # Brand terms
    brand_terms = ['Alphatex', 'luxury fashion Bangladesh', 'premium fashion BD']
    for t in brand_terms:
        if t.lower() not in seen:
            seen.add(t.lower())
            unique.append(t)

    return _truncate(', '.join(unique), 250, suffix='')


def generate_image_alt_text(name: str, slot_label: str = 'Hero',
                             category_name: str = '') -> str:
    """
    Generate descriptive image ALT text for a product image slot.
    """
    slot_map = {
        'Hero':        f"{name} — Front View | Alphatex",
        'Alternate':   f"{name} — Alternate View | Alphatex",
        'Detail':      f"{name} — Close-Up Detail | Alphatex",
        'Lifestyle':   f"{name} — Lifestyle Shot | Alphatex",
        'Scale':       f"{name} — Size Reference | Alphatex",
        'Infographic': f"{name} — Features & Specifications | Alphatex",
        'In the Box':  f"{name} — What\'s in the Box | Alphatex",
    }
    return slot_map.get(slot_label, f"{name} | Alphatex {category_name}").strip(' |')


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
    cat_id   = product.category_id if hasattr(product, 'category_id') else ''

    fields = {}

    # Slug — always regenerate so name changes are reflected
    fields['slug'] = generate_slug(product.name, product.id)

    # Meta title
    if force or not product.meta_title:
        fields['meta_title'] = generate_meta_title(product.name,
                                                    category_name=cat_name)

    # Meta description
    if force or not product.meta_description:
        fields['meta_description'] = generate_meta_description(
            product.description, product.name, cat_name
        )

    # Meta keywords
    if force or not product.meta_keywords:
        fields['meta_keywords'] = generate_meta_keywords(
            product.name, cat_name, category_id=cat_id
        )

    return fields


def apply_seo_fields(product, force: bool = False) -> None:
    """
    Convenience wrapper: compute and apply SEO fields directly to the product object.
    Caller is responsible for committing the session.
    """
    fields = generate_seo_fields(product, force=force)
    for key, value in fields.items():
        setattr(product, key, value)
