from flask import Blueprint, render_template, request, jsonify
from extensions import db
from models import Category, Product, CarouselSlide, IMAGE_SLOT_LABELS

shop_bp = Blueprint('shop', __name__)

@shop_bp.route('/')
def index():
    categories = Category.query.all()
    # Fetch 6 featured products for initial load
    featured = Product.query.filter_by(is_featured=True).limit(6).all()
    slides = CarouselSlide.query.filter_by(is_active=True).order_by(CarouselSlide.order).all()
    return render_template('index.html', categories=categories, featured=featured, slides=slides)

@shop_bp.route('/category/<cat_id>')
def category(cat_id):
    cat = Category.query.get_or_404(cat_id)
    products = Product.query.filter_by(category_id=cat_id).limit(8).all()
    return render_template('category.html', category=cat, products=products)

@shop_bp.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    related = Product.query.filter(
        Product.category_id == product.category_id,
        Product.id != product.id
    ).limit(4).all()
    return render_template('product.html', product=product, related=related,
                           slot_labels=IMAGE_SLOT_LABELS)

@shop_bp.route('/contact')
def contact():
    return render_template('contact.html')

# --- JSON API Endpoints for infinite scroll & search ---

@shop_bp.route('/api/products')
def api_products():
    page = request.args.get('page', 1, type=int)
    cat_id = request.args.get('category', None)
    per_page = 8
    query = Product.query
    if cat_id:
        query = query.filter_by(category_id=cat_id)
    total = query.count()
    products = query.offset((page - 1) * per_page).limit(per_page).all()
    return jsonify({
        'products': [
            {
                'id': p.id,
                'name': p.name,
                'price': p.price,
                'image': p.image,
                'category_id': p.category_id,
                'is_featured': p.is_featured,
                'hero': {
                    'src_600': p.hero_image.src(600),
                    'srcset': p.hero_image.srcset,
                    'blur': p.hero_image.blur_data_uri,
                    'alt': p.hero_image.alt_text
                } if p.hero_image else None
            }
            for p in products
        ],
        'has_more': (page * per_page) < total,
        'page': page,
    })

@shop_bp.route('/api/search')
def api_search():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify({'results': []})
    products = Product.query.filter(Product.name.ilike(f'%{q}%')).limit(6).all()
    return jsonify({
        'results': [
            {'id': p.id, 'name': p.name, 'price': p.price, 'image': p.image}
            for p in products
        ]
    })
