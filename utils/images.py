"""
utils/images.py — Automated image optimisation pipeline.

Usage:
    from utils.images import process_product_image, migrate_legacy_image

process_product_image(file_storage, product_id, slot) -> ProductImage
migrate_legacy_image(product)                          -> ProductImage | None
"""
import os, io, base64
from pathlib import Path
from PIL import Image

# Target sizes (width, px)
SIZES = [300, 600, 1200, 2000]
WEBP_QUALITY = 82          # 80-85 is the sweet-spot (>300KB risk below 80)
THUMB_MAX_BYTES = 50_000   # 50 KB
HERO_MAX_BYTES  = 300_000  # 300 KB
BLUR_SIZE = (20, 20)

SLOT_TYPES = {
    1: 'hero', 2: 'alternate', 3: 'detail',
    4: 'lifestyle', 5: 'scale', 6: 'infographic', 7: 'box',
}


def _products_dir(product_id: int) -> Path:
    base = Path(__file__).parent.parent / 'static' / 'images' / 'products' / str(product_id)
    base.mkdir(parents=True, exist_ok=True)
    return base


def _make_blur_uri(img: Image.Image) -> str:
    """Generate a tiny 20×20 base64-encoded WebP for the blur-up placeholder."""
    tiny = img.copy().convert('RGB')
    tiny.thumbnail(BLUR_SIZE, Image.LANCZOS)
    buf = io.BytesIO()
    tiny.save(buf, 'WEBP', quality=40)
    encoded = base64.b64encode(buf.getvalue()).decode()
    return f'data:image/webp;base64,{encoded}'


def _save_sizes(img: Image.Image, out_dir: Path, base_name: str):
    """Save the image at all responsive breakpoints as WebP."""
    orig_w, orig_h = img.size
    for w in SIZES:
        if w > orig_w:
            # Upscaling not allowed — skip sizes larger than source
            h = orig_h
            sized = img
        else:
            h = int(orig_h * (w / orig_w))
            sized = img.copy()
            sized = sized.resize((w, h), Image.LANCZOS)

        buf = io.BytesIO()
        sized.convert('RGB').save(buf, 'WEBP', quality=WEBP_QUALITY, method=6)
        size_bytes = buf.tell()

        # Adaptive quality drop to hit size targets
        if w <= 300 and size_bytes > THUMB_MAX_BYTES:
            buf = io.BytesIO()
            sized.convert('RGB').save(buf, 'WEBP', quality=65, method=6)
        elif w >= 1200 and size_bytes > HERO_MAX_BYTES:
            buf = io.BytesIO()
            sized.convert('RGB').save(buf, 'WEBP', quality=75, method=6)

        out_path = out_dir / f'{base_name}_{w}.webp'
        out_path.write_bytes(buf.getvalue())


def process_product_image(file_storage, product_id: int, slot: int,
                           alt_text: str = '') -> dict:
    """
    Process an uploaded FileStorage object.
    Returns a dict of fields ready to create a ProductImage record.
    """
    SLOT_TYPES = {
        1: 'hero', 2: 'alternate', 3: 'detail', 4: 'detail',
        5: 'lifestyle', 6: 'scale', 7: 'box'
    }
    image_type = SLOT_TYPES.get(slot, 'hero')
    base_name = f'p{product_id}_slot{slot}'
    out_dir = _products_dir(product_id)

    img = Image.open(file_storage.stream)
    img.load()  # force full read before stream closes

    blur_uri = _make_blur_uri(img)
    _save_sizes(img, out_dir, base_name)

    return {
        'product_id': product_id,
        'slot': slot,
        'image_type': image_type,
        'base_name': base_name,
        'alt_text': alt_text or f'Product image — {image_type}',
        'blur_data_uri': blur_uri,
    }


def process_product_image_from_path(src_path: str, product_id: int, slot: int,
                                     alt_text: str = '') -> dict:
    """
    Process an image from a filesystem path (used for migration).
    Returns a dict of fields ready to create a ProductImage record.
    """
    image_type = SLOT_TYPES.get(slot, 'hero')
    base_name = f'p{product_id}_slot{slot}'
    out_dir = _products_dir(product_id)

    if not Path(src_path).exists():
        return None

    img = Image.open(src_path)
    img.load()

    blur_uri = _make_blur_uri(img)
    _save_sizes(img, out_dir, base_name)

    return {
        'product_id': product_id,
        'slot': slot,
        'image_type': image_type,
        'base_name': base_name,
        'alt_text': alt_text,
        'blur_data_uri': blur_uri,
    }


def migrate_legacy_image(product, static_root: str) -> bool:
    """
    Convert a Product's legacy `.image` field (e.g. 'product_1.jpg') into a
    slot-1 ProductImage record using the optimisation pipeline.
    Returns True if migration ran, False if already migrated or file missing.
    """
    from models import ProductImage
    from extensions import db

    # Already migrated?
    if ProductImage.query.filter_by(product_id=product.id, slot=1).first():
        return False

    src = os.path.join(static_root, 'images', product.image)
    fields = process_product_image_from_path(src, product.id, 1, alt_text=product.name)
    if not fields:
        return False

    pi = ProductImage(**fields)
    db.session.add(pi)
    db.session.commit()
    print(f'[Migration] Product {product.id} "{product.name}" -> hero WebP created.')
    return True


def optimize_and_save_image(file_storage, dest_dir, filename_base, max_width=None, quality=82) -> str:
    """
    Reads an uploaded file (like a FileStorage object), converts it to WebP format,
    resizes it if it exceeds max_width (retaining aspect ratio), optimizes it, and
    saves it to dest_dir.
    Returns the new filename (e.g., 'filename_base.webp').
    """
    img = Image.open(file_storage.stream)
    img.load()
    
    # Handle transparency / modes
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        img = img.convert('RGBA')
    else:
        img = img.convert('RGB')
        
    orig_w, orig_h = img.size
    if max_width and orig_w > max_width:
        h = int(orig_h * (max_width / orig_w))
        img = img.resize((max_width, h), Image.LANCZOS)
        
    out_filename = f"{filename_base}.webp"
    out_path = Path(dest_dir) / out_filename
    os.makedirs(dest_dir, exist_ok=True)
    
    img.save(out_path, 'WEBP', quality=quality, method=6)
    return out_filename

