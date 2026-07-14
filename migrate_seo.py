import os
from app import app
from extensions import db
from models import Product
from utils.seo import apply_seo_fields

def migrate():
    print("Starting SEO migration...")
    with app.app_context():
        products = Product.query.all()
        updated = 0
        for p in products:
            print(f"Migrating [{p.id}] {p.name}...")
            apply_seo_fields(p, force=True)
            updated += 1
            print(f"  -> Slug: {p.slug}")
            print(f"  -> Title: {p.meta_title}")
        
        db.session.commit()
        print(f"\nSuccessfully migrated {updated} products.")

if __name__ == '__main__':
    migrate()
