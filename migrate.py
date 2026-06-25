import os

def migrate_legacy_images(app):
    """One-time migration: convert all legacy product JPGs to WebP + create ProductImage records."""
    import sys
    sys.path.insert(0, app.root_path)
    with app.app_context():
        from models import Product
        from utils.images import migrate_legacy_image
        static_root = os.path.join(app.root_path, 'static')
        products = Product.query.all()
        migrated = 0
        for p in products:
            if migrate_legacy_image(p, static_root):
                migrated += 1
        if migrated:
            print(f'[Migration] {migrated} product image(s) converted to WebP.')
