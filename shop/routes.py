from flask import Blueprint, render_template, request, jsonify, url_for, redirect
from flask_login import login_required, current_user
from extensions import db, limiter
from models import Category, Product, CarouselSlide, IMAGE_SLOT_LABELS, Offer

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

@shop_bp.route('/offer/<slug>')
def offer(slug):
    offer_obj = Offer.query.filter_by(slug=slug).first_or_404()
    if not offer_obj.is_active:
        return "Offer is currently inactive.", 404
    products = Product.query.filter_by(offer_id=offer_obj.id).all()
    return render_template('offer.html', offer=offer_obj, products=products)

@shop_bp.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    related = Product.query.filter(
        Product.category_id == product.category_id,
        Product.id != product.id
    ).limit(4).all()
    
    unique_colors = []
    unique_sizes = []
    if product.variants:
        colors_seen = set()
        sizes_seen = set()
        for v in product.variants:
            if v.color and v.color not in colors_seen:
                colors_seen.add(v.color)
                unique_colors.append({
                    'name': v.color, 
                    'slot': v.image.slot if v.image else None,
                    'id': v.id
                })
            if v.size and v.size not in sizes_seen:
                sizes_seen.add(v.size)
                unique_sizes.append(v.size)
                
    return render_template('product.html', product=product, related=related,
                           slot_labels=IMAGE_SLOT_LABELS,
                           unique_colors=unique_colors,
                           unique_sizes=unique_sizes)

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
                'compare_at_price': p.compare_at_price,
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
            {'id': p.id, 'name': p.name, 'price': p.price, 'compare_at_price': p.compare_at_price, 'image': p.image}
            for p in products
        ]
    })


@shop_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
@limiter.limit('10/minute')
def checkout():
    from models import DeliveryAddress, Order, OrderItem, Product
    
    if request.method == 'POST':
        data = request.get_json() or {}
        address_id = data.get('address_id')
        cart_items = data.get('items', [])
        order_notes = data.get('order_notes', '').strip()
        
        if not address_id:
            return jsonify({'error': 'Please select a delivery address.'}), 400
        if not cart_items:
            return jsonify({'error': 'Your cart is empty.'}), 400
            
        addr = DeliveryAddress.query.filter_by(id=address_id, user_id=current_user.id).first()
        if not addr:
            return jsonify({'error': 'Invalid delivery address.'}), 400
            
        # Create order
        total = 0.0
        order = Order(
            user_id=current_user.id,
            address_id=addr.id,
            shipping_address=addr.full_address,
            order_notes=order_notes,
            status='Pending'
        )
        db.session.add(order)
        db.session.flush()  # Generate order.id
        
        for item in cart_items:
            product_id = item.get('id')
            qty = int(item.get('qty', 1))
            prod = Product.query.get(product_id)
            if not prod:
                continue
            
            # Clean price string (e.g. "৳450.00" -> 450.00)
            raw_price = prod.price.replace('$', '').replace('৳', '').replace(',', '').strip()
            try:
                price_val = float(raw_price)
            except ValueError:
                price_val = 0.0
                
            item_total = price_val * qty
            total += item_total
            
            order_item = OrderItem(
                order_id=order.id,
                product_id=product_id,
                quantity=qty,
                price_at_purchase=price_val
            )
            db.session.add(order_item)
            
        order.total_amount = total
        db.session.commit()
        
        return jsonify({
            'success': True,
            'order_id': order.id,
            'redirect_url': url_for('user.order_detail', order_id=order.id)
        })
        
    addresses = DeliveryAddress.query.filter_by(user_id=current_user.id)\
                                 .order_by(DeliveryAddress.is_default.desc(),
                                           DeliveryAddress.created_at.desc()).all()
    from models import ADDRESS_LABELS
    return render_template('checkout.html', addresses=addresses, labels=ADDRESS_LABELS)


@shop_bp.route('/checkout/api/address/add', methods=['POST'])
@login_required
@limiter.limit('10/minute')
def checkout_add_address():
    from models import DeliveryAddress, ADDRESS_LABELS
    f = request.get_json() or {}
    recipient_name = f.get('recipient_name', '').strip()
    phone = f.get('phone', '').strip()
    division = f.get('division', '').strip()
    district = f.get('district', '').strip()
    upazila = f.get('upazila', '').strip()
    union_ward = f.get('union_ward', '').strip()
    area = f.get('area', '').strip()
    road = f.get('road', '').strip()
    house_no = f.get('house_no', '').strip()
    apartment = f.get('apartment', '').strip()
    postal_code = f.get('postal_code', '').strip()
    delivery_instructions = f.get('delivery_instructions', '').strip()
    maps_link = f.get('maps_link', '').strip()
    label = f.get('label', 'Home').strip()
    is_default = bool(f.get('is_default'))
    
    # Normalise phone number
    if phone.startswith('01') and len(phone) == 11:
        phone = '+88' + phone
    elif phone.startswith('8801') and len(phone) == 13:
        phone = '+' + phone

    if not recipient_name or not phone or not division or not district or not upazila:
        return jsonify({'error': 'Please fill all required fields.'}), 400

    if label not in ADDRESS_LABELS:
        label = 'Home'

    if is_default:
        DeliveryAddress.query.filter_by(user_id=current_user.id).update({'is_default': False})

    # If first address, make default
    count = DeliveryAddress.query.filter_by(user_id=current_user.id).count()
    if count == 0:
        is_default = True

    addr = DeliveryAddress(
        user_id=current_user.id,
        recipient_name=recipient_name,
        phone=phone,
        division=division,
        district=district,
        upazila=upazila,
        union_ward=union_ward or None,
        area=area or None,
        road=road or None,
        house_no=house_no or None,
        apartment=apartment or None,
        postal_code=postal_code or None,
        delivery_instructions=delivery_instructions or None,
        maps_link=maps_link or None,
        label=label,
        is_default=is_default
    )
    db.session.add(addr)
    db.session.commit()

    return jsonify({
        'success': True,
        'address': {
            'id': addr.id,
            'recipient_name': addr.recipient_name,
            'phone': addr.phone,
            'full_address': addr.full_address,
            'label': addr.label,
            'is_default': addr.is_default
        }
    })
