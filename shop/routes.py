import json
from flask import Blueprint, render_template, request, jsonify, url_for, redirect, Response
from flask_login import login_required, current_user
from extensions import db, limiter
from models import Category, Product, CarouselSlide, IMAGE_SLOT_LABELS, Offer

shop_bp = Blueprint('shop', __name__)

def check_maintenance():
    from models import SiteSettings
    try:
        m = SiteSettings.query.filter_by(key='maintenance_mode').first()
        return m and m.value == 'true'
    except Exception:
        return False

@shop_bp.route('/')
def index():
    categories = Category.query.all()
    if check_maintenance():
        featured = []
        slides = []
    else:
        ip = request.remote_addr
        preferred_category_id = None
        if ip:
            from sqlalchemy import func
            from models import ProductViewLog
            try:
                most_viewed_cat = db.session.query(
                    ProductViewLog.category_id,
                    func.count(ProductViewLog.id).label('count')
                ).filter(ProductViewLog.ip_address == ip).group_by(ProductViewLog.category_id).order_by(db.desc('count')).first()
                if most_viewed_cat:
                    preferred_category_id = most_viewed_cat[0]
            except Exception:
                pass

        all_products = Product.query.all()
        if preferred_category_id:
            pref_featured = [p for p in all_products if p.category_id == preferred_category_id and p.is_featured]
            pref_normal = [p for p in all_products if p.category_id == preferred_category_id and not p.is_featured]
            other_featured = [p for p in all_products if p.category_id != preferred_category_id and p.is_featured]
            other_normal = [p for p in all_products if p.category_id != preferred_category_id and not p.is_featured]
            
            import random
            random.shuffle(pref_normal)
            random.shuffle(other_normal)
            
            featured = (pref_featured + pref_normal + other_featured + other_normal)[:6]
        else:
            featured_prods = [p for p in all_products if p.is_featured]
            normal_prods = [p for p in all_products if not p.is_featured]
            
            import random
            random.shuffle(normal_prods)
            featured = (featured_prods + normal_prods)[:6]
            
        slides = CarouselSlide.query.filter_by(is_active=True).order_by(CarouselSlide.order).all()
    return render_template('index.html', categories=categories, featured=featured, slides=slides)

@shop_bp.route('/category/<cat_id>')
def category(cat_id):
    cat = Category.query.get_or_404(cat_id)
    if check_maintenance():
        products = []
    else:
        products = Product.query.filter_by(category_id=cat_id).limit(8).all()
    return render_template('category.html', category=cat, products=products)

@shop_bp.route('/offer/<slug>')
def offer(slug):
    offer_obj = Offer.query.filter_by(slug=slug).first_or_404()
    if not offer_obj.is_active:
        return "Offer is currently inactive.", 404
    if check_maintenance():
        products = []
    else:
        products = Product.query.filter_by(offer_id=offer_obj.id).all()
    return render_template('offer.html', offer=offer_obj, products=products)

@shop_bp.route('/product/<int:product_id>')
def product_detail_legacy(product_id):
    product = Product.query.get_or_404(product_id)
    if not product.slug:
        from utils.seo import apply_seo_fields
        apply_seo_fields(product, force=False)
        db.session.commit()
    return redirect(url_for('shop.product_detail', slug=product.slug), code=301)

@shop_bp.route('/product/<slug>')
def product_detail(slug):
    if check_maintenance():
        from flask import abort
        abort(404)
    product = Product.query.filter_by(slug=slug).first_or_404()
    
    # Log product view by IP
    ip = request.remote_addr
    if ip:
        from models import ProductViewLog
        try:
            db.session.add(ProductViewLog(ip_address=ip, category_id=product.category_id))
            db.session.commit()
        except Exception:
            db.session.rollback()
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
                
    # ── Build absolute OG image URL ────────────────────────────────────
    base_url = request.url_root.rstrip('/')
    hero = product.hero_image
    if hero:
        og_image = base_url + hero.src(1200)
    elif product.image:
        og_image = base_url + '/static/images/' + product.image
    else:
        og_image = base_url + '/static/images/logo.webp'

    # ── Ensure SEO fields exist (back-fill on first view if missing) ───────
    if not product.meta_title or not product.slug:
        from utils.seo import apply_seo_fields
        apply_seo_fields(product, force=False)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

    # ── JSON-LD structured data (Product schema) ────────────────────────
    raw_price = product.price.replace('$', '').replace('৳', '').replace(',', '').strip()
    try:
        price_num = float(raw_price)
    except ValueError:
        price_num = 0.0

    availability = 'https://schema.org/InStock' if product.stock > 0 else 'https://schema.org/OutOfStock'

    jsonld = {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": product.name,
        "description": product.meta_description or '',
        "image": og_image,
        "url": base_url + url_for('shop.product_detail', slug=product.slug),
        "brand": {
            "@type": "Brand",
            "name": "Alphatex"
        },
        "category": product.category.name if product.category else '',
        "offers": {
            "@type": "Offer",
            "priceCurrency": "BDT",
            "price": f"{price_num:.2f}",
            "availability": availability,
            "url": base_url + url_for('shop.product_detail', slug=product.slug),
            "seller": {
                "@type": "Organization",
                "name": "Alphatex"
            }
        }
    }
    product_jsonld = json.dumps(jsonld, ensure_ascii=False)

    return render_template('product.html', product=product, related=related,
                           slot_labels=IMAGE_SLOT_LABELS,
                           unique_colors=unique_colors,
                           unique_sizes=unique_sizes,
                           og_image=og_image,
                           product_jsonld=product_jsonld)

@shop_bp.route('/contact', methods=['GET', 'POST'])
@limiter.limit('10/minute')
def contact():
    if request.method == 'POST':
        # Accept JSON payloads for AJAX form submission
        data = request.get_json() or {}
        
        # Honeypot: bots fill the hidden field, humans leave it empty
        if data.get('website_url', '').strip():
            from flask import abort
            abort(403)

        # Turnstile verification
        from auth.routes import verify_turnstile
        cf_token = data.get('cf-turnstile-response')
        if not verify_turnstile(cf_token):
            return jsonify({'error': 'Security verification failed. Please try again.'}), 400

        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        subject = data.get('subject', '').strip()
        message = data.get('message', '').strip()
        phone = data.get('phone', '').strip()

        if not name or not email or not subject or not message:
            return jsonify({'error': 'Please fill all required fields.'}), 400

        from models import ContactMessage
        msg = ContactMessage(name=name, email=email, subject=subject, message=message)
        # Optionally save phone/alt contact details in note or extension if schema is exact, 
        # but our schema has name, email, subject, message, status. Let's keep it clean:
        db.session.add(msg)
        db.session.commit()
        return jsonify({'ok': True})
    return render_template('contact.html')

@shop_bp.route('/subscribe-newsletter', methods=['POST'])
@limiter.limit('5/minute')
def subscribe_newsletter():
    data = request.get_json() or {}
    email = data.get('email', '').strip()
    if not email:
        return jsonify({'error': 'Email address is required.'}), 400
    
    import re
    if not re.match(r'[^@]+@[^@]+\.[^@]+', email):
        return jsonify({'error': 'Invalid email address.'}), 400
        
    from models import NewsletterSubscriber
    existing = NewsletterSubscriber.query.filter_by(email=email).first()
    if existing:
        return jsonify({'error': 'This email is already subscribed.'}), 400
        
    try:
        sub = NewsletterSubscriber(email=email)
        db.session.add(sub)
        db.session.commit()
        return jsonify({'ok': True})
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred. Please try again.'}), 500

@shop_bp.route('/faq')
def faq():
    return render_template('faq.html')

@shop_bp.route('/shipping')
def shipping():
    return render_template('shipping.html')

@shop_bp.route('/size-guide')
def size_guide():
    return render_template('size_guide.html')

@shop_bp.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@shop_bp.route('/terms')
def terms():
    return render_template('terms.html')

@shop_bp.route('/cookie-policy')
def cookie_policy():
    return render_template('cookie_policy.html')

# --- JSON API Endpoints for infinite scroll & search ---

@shop_bp.route('/api/products')
@limiter.limit('60/minute')
def api_products():
    if check_maintenance():
        return jsonify({'products': [], 'has_more': False, 'page': 1})
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
                'stock': p.stock,
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
@limiter.limit('30/minute')
def api_search():
    if check_maintenance():
        return jsonify({'results': []})
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
@limiter.limit('10/minute')
def checkout():
    from models import DeliveryAddress, Order, OrderItem, Product
    
    if request.method == 'POST':
        data = request.get_json() or {}
        cart_items = data.get('items', [])
        order_notes = data.get('order_notes', '').strip()
        
        if not cart_items:
            return jsonify({'error': 'Your cart is empty.'}), 400
            
        if current_user.is_authenticated:
            address_id = data.get('address_id')
            if not address_id:
                return jsonify({'error': 'Please select a delivery address.'}), 400
            addr = DeliveryAddress.query.filter_by(id=address_id, user_id=current_user.id).first()
            if not addr:
                return jsonify({'error': 'Invalid delivery address.'}), 400
            
            user_id = current_user.id
            addr_id = addr.id
            shipping_address = addr.full_address
            redirect_url = url_for('user.order_detail', order_id=0) # will replace below
        else:
            # Guest checkout
            guest_name = data.get('guest_name', '').strip()
            guest_phone = data.get('guest_phone', '').strip()
            guest_address = data.get('guest_address', '').strip()
            
            if not guest_name or not guest_phone or not guest_address:
                return jsonify({'error': 'Please fill all guest recipient information.'}), 400
                
            user_id = None
            addr_id = None
            shipping_address = f"Recipient Name: {guest_name}\nPhone: {guest_phone}\nAddress: {guest_address}"
            redirect_url = url_for('shop.guest_order_success', order_id=0) # will replace below
            
        # Create order
        total = 0.0
        order = Order(
            user_id=user_id,
            address_id=addr_id,
            shipping_address=shipping_address,
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
                return jsonify({'error': f"Product '{item.get('name', 'Unknown')}' is no longer available. Please remove it from your cart."}), 400
            
            if prod.stock < qty:
                return jsonify({'error': f"Only {prod.stock} units of '{prod.name}' are available. Please reduce your quantity."}), 400
            
            prod.stock -= qty
            
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
        
        if current_user.is_authenticated:
            final_redirect = url_for('user.order_detail', order_id=order.id)
        else:
            final_redirect = url_for('shop.guest_order_success', order_id=order.id)
            
        return jsonify({
            'success': True,
            'order_id': order.id,
            'redirect_url': final_redirect
        })
        
    if current_user.is_authenticated:
        addresses = DeliveryAddress.query.filter_by(user_id=current_user.id)\
                                     .order_by(DeliveryAddress.is_default.desc(),
                                               DeliveryAddress.created_at.desc()).all()
    else:
        addresses = []
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


@shop_bp.route('/checkout/success/<int:order_id>')
def guest_order_success(order_id):
    from models import Order
    from flask import abort
    order = Order.query.get_or_404(order_id)
    if order.user_id is not None:
        if not current_user.is_authenticated or current_user.id != order.user_id:
            abort(403)
    return render_template('checkout_success.html', order=order)


# ── SEO: Sitemap ────────────────────────────────────────────────────────────

@shop_bp.route('/sitemap.xml')
def sitemap():
    """Generate an XML sitemap for all public product pages."""
    base_url = request.url_root.rstrip('/')
    products = Product.query.all()

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']

    # Homepage
    lines.append(f'  <url><loc>{base_url}/</loc><priority>1.0</priority></url>')

    # Category pages
    for cat in Category.query.all():
        lines.append(
            f'  <url>'
            f'<loc>{base_url}/category/{cat.id}</loc>'
            f'<priority>0.7</priority>'
            f'</url>'
        )

    # Product pages
    for p in products:
        loc = f'{base_url}/product/{p.slug}'
        lines.append(
            f'  <url>'
            f'<loc>{loc}</loc>'
            f'<priority>0.8</priority>'
            f'<changefreq>weekly</changefreq>'
            f'</url>'
        )

    lines.append('</urlset>')
    xml = '\n'.join(lines)
    return Response(xml, mimetype='application/xml')


# ── SEO: Robots.txt ─────────────────────────────────────────────────────────

@shop_bp.route('/robots.txt')
def robots_txt():
    """Serve a robots.txt that allows all bots and points to the sitemap."""
    base_url = request.url_root.rstrip('/')
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin/\n"
        "Disallow: /checkout/\n"
        f"Sitemap: {base_url}/sitemap.xml\n"
    )
    return Response(content, mimetype='text/plain')


@shop_bp.route('/api/ai/chat', methods=['POST'])
@limiter.limit('30/minute')
def api_ai_chat():
    import os, requests
    from models import Product
    
    # Retrieve Gemini API Key from environment
    gemini_key = os.environ.get('GEMINI_API_KEY')
    if not gemini_key:
        return jsonify({'error': 'AI chat is currently unavailable.'}), 503
        
    data = request.get_json() or {}
    user_message = data.get('message', '').strip()
    history = data.get('history', [])
    
    if not user_message:
        return jsonify({'error': 'Message is required.'}), 400
        
    # Retrieve product catalog to build RAG context
    try:
        products = Product.query.all()
        catalog_lines = []
        for p in products:
            cat_name = p.category.name if p.category else 'Unknown'
            status = 'In Stock' if p.stock > 0 else 'Out of Stock'
            catalog_lines.append(
                f"- Name: {p.name}\n"
                f"  Price: {p.price} BDT\n"
                f"  Category: {cat_name}\n"
                f"  Status: {status} (Stock: {p.stock})\n"
                f"  Description: {p.description or 'Premium exclusive item'}\n"
                f"  Link: /product/{p.id}"
            )
        catalog_context = "\n".join(catalog_lines)
    except Exception as e:
        catalog_context = "No products found."
        
    system_instruction = (
        "You are Alphatex AI Concierge, a luxury customer service assistant for Alphatex, "
        "a high-end, premium clothing boutique. Your voice must be sophisticated, helpful, polite, and welcoming (concierge tone).\n\n"
        "Here is our live product catalog:\n"
        f"{catalog_context}\n\n"
        "Guidelines:\n"
        "1. Recommend specific products from our catalog that match the user's needs. Highlight their price in BDT and suggest visiting their link.\n"
        "2. Keep responses brief, structured with bullet points or paragraphs, and easy to read. Do not write extremely long paragraphs.\n"
        "3. If a product is Out of Stock, politely let them know and suggest an alternative that is In Stock.\n"
        "4. For general inquiries (shipping, returns, size guide, contact), suggest checking the links at the bottom of the page.\n"
        "5. If the user asks about WhatsApp or Messenger, note that they can chat directly with sales representatives by clicking the respective floating buttons on the screen.\n"
        "6. Do not speculate or make up products that are not in the catalog. Only discuss real products listed above."
    )
    
    # Format messages for Gemini API
    contents = []
    for h in history:
        role = 'user' if h.get('role') == 'user' else 'model'
        contents.append({
            'role': role,
            'parts': [{'text': h.get('text', '')}]
        })
        
    # Append current message
    contents.append({
        'role': 'user',
        'parts': [{'text': user_message}]
    })
    
    # Request payload
    payload = {
        'contents': contents,
        'systemInstruction': {
            'parts': [{'text': system_instruction}]
        },
        'generationConfig': {
            'temperature': 0.4,
            'topK': 40,
            'topP': 0.95,
            'maxOutputTokens': 1024
        }
    }
    
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
    
    try:
        res = requests.post(api_url, json=payload, headers={'Content-Type': 'application/json'}, timeout=10)
        if res.status_code == 200:
            res_data = res.json()
            candidates = res_data.get('candidates', [])
            if candidates:
                bot_text = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                return jsonify({'reply': bot_text})
            return jsonify({'error': 'No response candidate received.'}), 500
        else:
            return jsonify({'error': f"Gemini API returned status code {res.status_code}."}), 500
    except Exception as e:
        return jsonify({'error': f"Failed to connect to AI server: {str(e)}"}), 500
