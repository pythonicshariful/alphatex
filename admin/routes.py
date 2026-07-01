import io
import base64
import pyotp
import qrcode
from datetime import datetime, timedelta
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session, current_app, make_response)
from functools import wraps
import os
from werkzeug.utils import secure_filename
from utils.images import process_product_image
from functools import wraps
from extensions import db, limiter
from models import AdminUser, AdminLoginLog, ADMIN_ROLES, Category, Product, User, CarouselSlide, ProductImage, Offer

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# -------------------------------------------------------
# Helpers
# -------------------------------------------------------

def log_attempt(admin, status, request):
    log = AdminLoginLog(
        admin_id=admin.id if admin else None,
        email=request.form.get('email', ''),
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string[:250],
        status=status
    )
    db.session.add(log)
    db.session.commit()

def require_admin(module=None):
    """Decorator: verify admin session + optional module permission."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            admin_id = session.get('admin_id')
            if not admin_id:
                return redirect(url_for('admin.login'))
            admin = AdminUser.query.get(admin_id)
            if not admin:
                session.pop('admin_id', None)
                return redirect(url_for('admin.login'))
            # Session timeout
            last_activity = session.get('admin_last_activity')
            timeout = current_app.config.get('ADMIN_SESSION_TIMEOUT', 1800)
            if last_activity and (datetime.utcnow().timestamp() - last_activity) > timeout:
                session.pop('admin_id', None)
                flash('Session expired. Please log in again.', 'warning')
                return redirect(url_for('admin.login'))
            session['admin_last_activity'] = datetime.utcnow().timestamp()
            if module and not admin.has_permission(module):
                flash('Access denied.', 'error')
                return redirect(url_for('admin.dashboard'))
            return f(admin, *args, **kwargs)
        return decorated
    return decorator

def check_ip_whitelist():
    allowed = current_app.config.get('ADMIN_ALLOWED_IPS', [])
    if allowed and request.remote_addr not in allowed:
        return False
    return True

def enforce_password_policy(password):
    """8+ chars, uppercase, digit, special char."""
    import re
    if len(password) < 8:
        return False, 'Password must be at least 8 characters.'
    if not re.search(r'[A-Z]', password):
        return False, 'Password must contain at least one uppercase letter.'
    if not re.search(r'\d', password):
        return False, 'Password must contain at least one number.'
    if not re.search(r'[^A-Za-z0-9]', password):
        return False, 'Password must contain at least one special character.'
    return True, ''


# -------------------------------------------------------
# Admin Login Flow
# -------------------------------------------------------

@admin_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('10/minute')
def login():
    if session.get('admin_id') and session.get('admin_2fa_verified'):
        return redirect(url_for('admin.dashboard'))
    if not check_ip_whitelist():
        return render_template('admin/login.html', error='Access denied from your IP address.')
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        admin = AdminUser.query.filter_by(email=email).first()

        # Account locked?
        if admin and admin.is_locked:
            if admin.locked_until and datetime.utcnow() < admin.locked_until:
                log_attempt(admin, 'locked', request)
                remaining = int((admin.locked_until - datetime.utcnow()).total_seconds() / 60)
                return render_template('admin/login.html',
                    error=f'Account locked. Try again in {remaining} minutes.')
            else:
                admin.is_locked = False
                admin.failed_attempts = 0
                db.session.commit()

        if not admin or not admin.check_password(password):
            if admin:
                admin.failed_attempts += 1
                max_attempts = current_app.config.get('ADMIN_MAX_FAILED_ATTEMPTS', 5)
                if admin.failed_attempts >= max_attempts:
                    admin.is_locked = True
                    admin.locked_until = datetime.utcnow() + timedelta(
                        minutes=current_app.config.get('ADMIN_LOCKOUT_MINUTES', 30))
                    db.session.commit()
                    log_attempt(admin, 'locked', request)
                    return render_template('admin/login.html',
                        error='Too many failed attempts. Account locked for 30 minutes.')
                db.session.commit()
            log_attempt(admin, 'fail_password', request)
            return render_template('admin/login.html', error='Invalid email or password.')

        # Credentials valid — proceed immediately
        admin.failed_attempts = 0
        admin.last_login = datetime.utcnow()
        db.session.commit()
        session['admin_id'] = admin.id
        session['admin_2fa_verified'] = True  # Keep for compatibility
        session['admin_last_activity'] = datetime.utcnow().timestamp()
        log_attempt(admin, 'success', request)
        return redirect(url_for('admin.dashboard'))

    return render_template('admin/login.html')


@admin_bp.route('/2fa', methods=['GET', 'POST'])
def two_factor():
    admin_id = session.get('admin_pending_id')
    if not admin_id:
        return redirect(url_for('admin.login'))
    admin = AdminUser.query.get(admin_id)
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        if admin.verify_totp(code):
            session.pop('admin_pending_id', None)
            session['admin_id'] = admin.id
            session['admin_2fa_verified'] = True
            session['admin_last_activity'] = datetime.utcnow().timestamp()
            log_attempt(admin, 'success', request)
            return redirect(url_for('admin.dashboard'))
        log_attempt(admin, 'fail_2fa', request)
        return render_template('admin/2fa.html', error='Invalid code. Please try again.')
    return render_template('admin/2fa.html')


@admin_bp.route('/setup-2fa', methods=['GET', 'POST'])
def setup_2fa():
    admin_id = session.get('admin_pending_id')
    if not admin_id:
        return redirect(url_for('admin.login'))
    admin = AdminUser.query.get(admin_id)
    if not admin.totp_secret:
        admin.totp_secret = pyotp.random_base32()
        db.session.commit()
    totp_uri = admin.get_totp_uri()
    # Generate QR code as base64 image
    img = qrcode.make(totp_uri)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        if admin.verify_totp(code):
            admin.is_2fa_enabled = True
            db.session.commit()
            session.pop('admin_pending_id', None)
            session['admin_id'] = admin.id
            session['admin_2fa_verified'] = True
            session['admin_last_activity'] = datetime.utcnow().timestamp()
            log_attempt(admin, 'success', request)
            flash('2FA enabled successfully!', 'success')
            return redirect(url_for('admin.dashboard'))
        return render_template('admin/setup_2fa.html', qr_b64=qr_b64,
                               secret=admin.totp_secret, error='Invalid code. Scan QR and try again.')
    return render_template('admin/setup_2fa.html', qr_b64=qr_b64, secret=admin.totp_secret)


@admin_bp.route('/logout')
def logout():
    session.pop('admin_id', None)
    session.pop('admin_2fa_verified', None)
    session.pop('admin_pending_id', None)
    return redirect(url_for('admin.login'))


# -------------------------------------------------------
# Admin Dashboard
# -------------------------------------------------------

@admin_bp.route('/')
@require_admin()
def dashboard(admin):
    from models import Order, AuditLog
    from sqlalchemy import func

    range_days = int(request.args.get('range', 30))
    since = datetime.utcnow() - timedelta(days=range_days)

    total_revenue = db.session.query(func.coalesce(func.sum(Order.total_amount), 0)).scalar() or 0
    orders_count  = Order.query.count()
    pending_count = Order.query.filter_by(status='Pending').count()

    # Revenue by day (last range_days)
    revenue_data = db.session.query(
        func.date(Order.created_at).label('day'),
        func.sum(Order.total_amount).label('rev')
    ).filter(Order.created_at >= since).group_by(func.date(Order.created_at)).all()

    # Build chart-friendly lists
    rev_labels = [str(r.day) for r in revenue_data]
    rev_values = [float(r.rev or 0) for r in revenue_data]

    # Orders by status
    order_statuses = ['Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled']
    order_counts   = [Order.query.filter_by(status=s).count() for s in order_statuses]

    # Products by category
    cat_labels = [c.name for c in Category.query.all()]
    cat_counts = [Product.query.filter_by(category_id=c.id).count() for c in Category.query.all()]

    # Recent audit log
    recent_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(8).all()

    stats = {
        'products':     Product.query.count(),
        'categories':   Category.query.count(),
        'users':        User.query.count(),
        'banned_users': User.query.filter_by(is_banned=True).count(),
        'admins':       AdminUser.query.count(),
        'orders':       orders_count,
        'pending':      pending_count,
        'revenue':      f"৳{total_revenue:,.2f}",
    }
    return render_template('admin/dashboard.html', admin=admin, stats=stats,
                           ADMIN_ROLES=ADMIN_ROLES, range_days=range_days,
                           rev_labels=rev_labels, rev_values=rev_values,
                           order_statuses=order_statuses, order_counts=order_counts,
                           cat_labels=cat_labels, cat_counts=cat_counts,
                           recent_logs=recent_logs)


@admin_bp.route('/orders')
@require_admin('orders')
def orders(admin):
    from models import Order
    all_orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', admin=admin, orders=all_orders)


@admin_bp.route('/order/<int:oid>', methods=['GET', 'POST'])
@require_admin('orders')
def order_detail(admin, oid):
    from models import Order, DeliveryAddress
    order = Order.query.get_or_404(oid)
    if request.method == 'POST':
        order.status = request.form.get('status', order.status)
        order.tracking_number = request.form.get('tracking_number', order.tracking_number)
        order.courier_name = request.form.get('courier_name', order.courier_name)
        order.courier_tracking = request.form.get('courier_tracking', order.courier_tracking)
        order.order_notes = request.form.get('order_notes', order.order_notes)

        # Update address details if form contains them
        if order.delivery_address:
            addr = order.delivery_address
            addr.recipient_name = request.form.get('recipient_name', addr.recipient_name)
            addr.phone = request.form.get('phone', addr.phone)
            addr.division = request.form.get('division', addr.division)
            addr.district = request.form.get('district', addr.district)
            addr.upazila = request.form.get('upazila', addr.upazila)
            addr.union_ward = request.form.get('union_ward', addr.union_ward)
            addr.area = request.form.get('area', addr.area)
            addr.road = request.form.get('road', addr.road)
            addr.house_no = request.form.get('house_no', addr.house_no)
            addr.apartment = request.form.get('apartment', addr.apartment)
            addr.postal_code = request.form.get('postal_code', addr.postal_code)
            addr.maps_link = request.form.get('maps_link', addr.maps_link)
        else:
            order.shipping_address = request.form.get('shipping_address', order.shipping_address)

        db.session.commit()
        flash('Order and shipping details updated successfully.', 'success')
        return redirect(url_for('admin.order_detail', oid=order.id))
    return render_template('admin/order_detail.html', admin=admin, order=order)


@admin_bp.route('/products')
@require_admin('products')
def products(admin):
    products = Product.query.all()
    categories = Category.query.all()
    return render_template('admin/products.html', admin=admin, products=products, categories=categories)


@admin_bp.route('/products/add', methods=['GET', 'POST'])
@require_admin('products')
def add_product(admin):
    categories = Category.query.all()
    offers = Offer.query.all()
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        compare_at_price = request.form.get('compare_at_price')
        category_id = request.form.get('category_id')
        offer_id = request.form.get('offer_id') or None
        is_featured = bool(request.form.get('is_featured'))
        description = request.form.get('description', '')
        
        p = Product(name=name, price=price, compare_at_price=compare_at_price, image='product_1.jpg',
                    category_id=category_id, offer_id=offer_id, is_featured=is_featured, description=description)
        db.session.add(p)
        db.session.commit()

        # Handle 7 image slots upload
        for slot in range(1, 8):
            file = request.files.get(f'image_slot_{slot}')
            if file and file.filename:
                fields = process_product_image(file, p.id, slot, alt_text=f"{name} view {slot}")
                img = ProductImage(**fields)
                db.session.add(img)
                # If it's slot 1, also update legacy image
                if slot == 1:
                    p.image = f'products/{p.id}/{fields["base_name"]}_600.webp'
                    
        # Handle variants arrays
        colors = request.form.getlist('v_color[]')
        sizes = request.form.getlist('v_size[]')
        skus = request.form.getlist('v_sku[]')
        stocks = request.form.getlist('v_stock[]')
        slots = request.form.getlist('v_image_slot[]')
        
        for i in range(len(colors)):
            v_color = colors[i].strip() if colors[i] else None
            v_size = sizes[i].strip() if sizes[i] else None
            if not v_color and not v_size:
                continue
                
            v_sku = skus[i].strip() if skus[i] else None
            v_stock = int(stocks[i]) if stocks[i].isdigit() else 0
            v_slot = int(slots[i]) if slots[i].isdigit() else None
            
            # Find the ProductImage with this slot if provided
            img_id = None
            if v_slot:
                img = ProductImage.query.filter_by(product_id=p.id, slot=v_slot).first()
                if img:
                    img_id = img.id
                    
            from models import ProductVariant
            pv = ProductVariant(
                product_id=p.id, color=v_color, size=v_size,
                sku=v_sku, stock=v_stock, image_id=img_id
            )
            db.session.add(pv)
            
        db.session.commit()
        flash(f'Product "{name}" added successfully.', 'success')
        return redirect(url_for('admin.products'))
        
    return render_template('admin/product_form.html', admin=admin, categories=categories, offers=offers, product=None)


@admin_bp.route('/products/edit/<int:pid>', methods=['GET', 'POST'])
@require_admin('products')
def edit_product(admin, pid):
    p = Product.query.get_or_404(pid)
    categories = Category.query.all()
    offers = Offer.query.all()
    
    if request.method == 'POST':
        p.name = request.form.get('name')
        p.price = request.form.get('price')
        p.compare_at_price = request.form.get('compare_at_price')
        p.category_id = request.form.get('category_id')
        p.offer_id = request.form.get('offer_id') or None
        p.is_featured = bool(request.form.get('is_featured'))
        p.description = request.form.get('description', '')
        
        # Handle 7 image slots upload
        for slot in range(1, 8):
            file = request.files.get(f'image_slot_{slot}')
            if file and file.filename:
                fields = process_product_image(file, p.id, slot, alt_text=f"{p.name} view {slot}")
                
                # Check if image for this slot already exists
                existing = next((img for img in p.images if img.slot == slot), None)
                if existing:
                    existing.blur_data_uri = fields['blur_data_uri']
                    existing.base_name = fields['base_name']
                else:
                    img = ProductImage(**fields)
                    db.session.add(img)
                
                if slot == 1:
                    p.image = f'products/{p.id}/{fields["base_name"]}_600.webp'
                    
        # Update variants (delete old and replace)
        from models import ProductVariant
        ProductVariant.query.filter_by(product_id=p.id).delete()
        
        colors = request.form.getlist('v_color[]')
        sizes = request.form.getlist('v_size[]')
        skus = request.form.getlist('v_sku[]')
        stocks = request.form.getlist('v_stock[]')
        slots = request.form.getlist('v_image_slot[]')
        
        for i in range(len(colors)):
            v_color = colors[i].strip() if colors[i] else None
            v_size = sizes[i].strip() if sizes[i] else None
            if not v_color and not v_size:
                continue
                
            v_sku = skus[i].strip() if skus[i] else None
            v_stock = int(stocks[i]) if stocks[i].isdigit() else 0
            v_slot = int(slots[i]) if slots[i].isdigit() else None
            
            img_id = None
            if v_slot:
                img = next((i for i in p.images if i.slot == v_slot), None)
                if img:
                    img_id = img.id
                    
            pv = ProductVariant(
                product_id=p.id, color=v_color, size=v_size,
                sku=v_sku, stock=v_stock, image_id=img_id
            )
            db.session.add(pv)
            
        db.session.commit()
        flash('Product updated successfully.', 'success')
        return redirect(url_for('admin.products'))
        
    return render_template('admin/product_form.html', admin=admin, categories=categories, offers=offers, product=p)


@admin_bp.route('/products/delete/<int:pid>', methods=['POST'])
@require_admin('products')
def delete_product(admin, pid):
    p = Product.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    flash('Product deleted.', 'success')
    return redirect(url_for('admin.products'))


# -------------------------------------------------------
# Categories CMS
# -------------------------------------------------------

@admin_bp.route('/categories', methods=['GET', 'POST'])
@require_admin('products')
def categories(admin):
    if request.method == 'POST':
        # Add new category
        cat_id = request.form.get('id')
        name = request.form.get('name')
        image = request.form.get('image', 'product_1.jpg')
        if Category.query.get(cat_id):
            flash('Category ID already exists.', 'error')
        else:
            cat = Category(id=cat_id, name=name, image=image)
            db.session.add(cat)
            db.session.commit()
            flash('Category added.', 'success')
        return redirect(url_for('admin.categories'))
        
    cats = Category.query.all()
    return render_template('admin/categories.html', admin=admin, categories=cats)

@admin_bp.route('/categories/delete/<string:cid>', methods=['POST'])
@require_admin('products')
def delete_category(admin, cid):
    cat = Category.query.get_or_404(cid)
    db.session.delete(cat)
    db.session.commit()
    flash('Category deleted.', 'success')
    return redirect(url_for('admin.categories'))

# -------------------------------------------------------
# Offers CMS
# -------------------------------------------------------

@admin_bp.route('/offers', methods=['GET', 'POST'])
@require_admin('products')
def offers(admin):
    if request.method == 'POST':
        title = request.form.get('title')
        slug = request.form.get('slug')
        is_active = request.form.get('is_active') == 'on'
        file = request.files.get('banner_image')
        
        banner_image = None
        if file and file.filename:
            from werkzeug.utils import secure_filename
            import os
            from flask import current_app
            filename = secure_filename(file.filename)
            upload_dir = os.path.join(current_app.root_path, 'static', 'images', 'offers')
            os.makedirs(upload_dir, exist_ok=True)
            filepath = os.path.join(upload_dir, filename)
            file.save(filepath)
            banner_image = filename
            
        if Offer.query.filter_by(slug=slug).first():
            flash('Offer slug already exists.', 'error')
        else:
            offer = Offer(title=title, slug=slug, banner_image=banner_image, is_active=is_active)
            db.session.add(offer)
            db.session.commit()
            flash('Offer created successfully.', 'success')
        return redirect(url_for('admin.offers'))
        
    offers = Offer.query.all()
    return render_template('admin/offers.html', admin=admin, offers=offers)

@admin_bp.route('/offers/delete/<int:oid>', methods=['POST'])
@require_admin('products')
def delete_offer(admin, oid):
    offer = Offer.query.get_or_404(oid)
    db.session.delete(offer)
    db.session.commit()
    flash('Offer deleted.', 'success')
    return redirect(url_for('admin.offers'))

# -------------------------------------------------------
# Carousel CMS
# -------------------------------------------------------

@admin_bp.route('/carousel', methods=['GET', 'POST'])
@require_admin('settings')
def carousel(admin):
    if request.method == 'POST':
        file = request.files.get('image')
        heading = request.form.get('heading')
        subheading = request.form.get('subheading')
        button_text = request.form.get('button_text')
        button_link = request.form.get('button_link')
        try:
            order = int(request.form.get('order', 0))
        except (TypeError, ValueError):
            order = 0
        
        if file and file.filename:
            filename = secure_filename(file.filename)
            upload_dir = os.path.join(current_app.root_path, 'static', 'images')
            os.makedirs(upload_dir, exist_ok=True)
            filepath = os.path.join(upload_dir, filename)
            file.save(filepath)
            
            slide = CarouselSlide(
                image=filename,
                heading=heading,
                subheading=subheading,
                button_text=button_text,
                button_link=button_link,
                order=order
            )
            db.session.add(slide)
            db.session.commit()
            flash('Slide added.', 'success')
        else:
            flash('Image is required.', 'error')
        return redirect(url_for('admin.carousel'))
        
    slides = CarouselSlide.query.order_by(CarouselSlide.order).all()
    return render_template('admin/carousel.html', admin=admin, slides=slides)

@admin_bp.route('/carousel/delete/<int:sid>', methods=['POST'])
@require_admin('settings')
def delete_carousel(admin, sid):
    s = CarouselSlide.query.get_or_404(sid)
    db.session.delete(s)
    db.session.commit()
    flash('Slide deleted.', 'success')
    return redirect(url_for('admin.carousel'))



@admin_bp.route('/login-history')
@require_admin('logs')
def login_history(admin):
    logs = AdminLoginLog.query.order_by(AdminLoginLog.timestamp.desc()).limit(200).all()
    return render_template('admin/login_history.html', admin=admin, logs=logs)


# ── Helpers ─────────────────────────────────────────────────

def log_audit(admin_obj, action, target_type=None, target_id=None, details=None):
    """Write an immutable audit entry."""
    from models import AuditLog
    entry = AuditLog(
        admin_id=admin_obj.id if admin_obj else None,
        admin_username=admin_obj.username if admin_obj else 'system',
        action=action, target_type=target_type,
        target_id=str(target_id) if target_id else None,
        details=details, ip_address=request.remote_addr
    )
    db.session.add(entry)
    db.session.commit()


# ── Audit Log ─────────────────────────────────────────────

@admin_bp.route('/audit-log')
@require_admin('logs')
def audit_log(admin):
    from models import AuditLog
    q = request.args.get('q', '').strip()
    query = AuditLog.query.order_by(AuditLog.timestamp.desc())
    if q:
        query = query.filter(
            (AuditLog.action.ilike(f'%{q}%')) |
            (AuditLog.admin_username.ilike(f'%{q}%')) |
            (AuditLog.details.ilike(f'%{q}%'))
        )
    logs = query.limit(300).all()
    return render_template('admin/audit_log.html', admin=admin, logs=logs, q=q)


# ── Security Center ──────────────────────────────────────

@admin_bp.route('/security', methods=['GET', 'POST'])
@require_admin('logs')
def security(admin):
    from models import IPRule, AdminLoginLog
    if request.method == 'POST':
        ip    = request.form.get('ip_address', '').strip()
        rtype = request.form.get('rule_type', 'blacklist')
        note  = request.form.get('note', '')
        if ip:
            existing = IPRule.query.filter_by(ip_address=ip).first()
            if not existing:
                rule = IPRule(ip_address=ip, rule_type=rtype, note=note)
                db.session.add(rule)
                db.session.commit()
                log_audit(admin, f'add_ip_{rtype}', 'ip_rule', ip, f'IP {ip} added to {rtype}')
                flash(f'IP {ip} added to {rtype}.', 'success')
            else:
                flash('IP rule already exists.', 'warning')
        return redirect(url_for('admin.security'))

    ip_rules     = IPRule.query.order_by(IPRule.created_at.desc()).all()
    locked_admins = AdminUser.query.filter_by(is_locked=True).all()
    recent_fails  = AdminLoginLog.query.filter(
        AdminLoginLog.status.in_(['fail_password', 'fail_2fa', 'locked'])
    ).order_by(AdminLoginLog.timestamp.desc()).limit(20).all()
    return render_template('admin/security.html', admin=admin,
                           ip_rules=ip_rules, locked_admins=locked_admins,
                           recent_fails=recent_fails)

@admin_bp.route('/security/delete-ip/<int:rid>', methods=['POST'])
@require_admin('logs')
def delete_ip_rule(admin, rid):
    from models import IPRule
    rule = IPRule.query.get_or_404(rid)
    ip = rule.ip_address
    db.session.delete(rule); db.session.commit()
    log_audit(admin, 'delete_ip_rule', 'ip_rule', ip, f'Removed IP rule for {ip}')
    flash(f'IP rule for {ip} removed.', 'success')
    return redirect(url_for('admin.security'))

@admin_bp.route('/security/unlock-admin/<int:aid>', methods=['POST'])
@require_admin('settings')
def unlock_admin(admin, aid):
    target = AdminUser.query.get_or_404(aid)
    target.is_locked = False; target.failed_attempts = 0; target.locked_until = None
    db.session.commit()
    log_audit(admin, 'unlock_admin', 'admin_user', aid, f'Unlocked admin {target.username}')
    flash(f'Admin {target.username} unlocked.', 'success')
    return redirect(url_for('admin.security'))


# ── Users (Enhanced) ─────────────────────────────────────

@admin_bp.route('/users')
@require_admin('users')
def users(admin):
    q = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '')
    query = User.query
    if q:
        query = query.filter(
            (User.phone.ilike(f'%{q}%')) |
            (User.email.ilike(f'%{q}%')) |
            (User.username.ilike(f'%{q}%'))
        )
    if status_filter == 'banned': query = query.filter_by(is_banned=True)
    elif status_filter == 'verified': query = query.filter_by(is_verified=True)
    all_users = query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', admin=admin, users=all_users, q=q, status_filter=status_filter)

@admin_bp.route('/users/<int:uid>/ban', methods=['POST'])
@require_admin('users')
def ban_user(admin, uid):
    user = User.query.get_or_404(uid)
    reason = request.form.get('reason', 'Violation of terms')
    user.is_banned = True; user.banned_reason = reason
    db.session.commit()
    log_audit(admin, 'ban_user', 'user', uid, f'Banned {user.email or user.phone}: {reason}')
    flash(f'User banned.', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:uid>/unban', methods=['POST'])
@require_admin('users')
def unban_user(admin, uid):
    user = User.query.get_or_404(uid)
    user.is_banned = False; user.banned_reason = None
    db.session.commit()
    log_audit(admin, 'unban_user', 'user', uid, f'Unbanned {user.email or user.phone}')
    flash('User unbanned.', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:uid>/impersonate', methods=['POST'])
@require_admin('settings')
def impersonate_user(admin, uid):
    user = User.query.get_or_404(uid)
    log_audit(admin, 'impersonate_user', 'user', uid, f'Admin impersonated user {user.email or user.phone}')
    session['impersonating'] = user.id
    session['impersonating_name'] = user.email or user.phone or str(user.id)
    from flask_login import login_user
    login_user(user)
    return redirect('/')

@admin_bp.route('/users/stop-impersonation')
def stop_impersonation(admin_id=None):
    uid = session.pop('impersonating', None)
    session.pop('impersonating_name', None)
    from flask_login import logout_user
    logout_user()
    flash('Impersonation ended.', 'info')
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/bulk', methods=['POST'])
@require_admin('users')
def bulk_user_action(admin):
    action = request.form.get('action')
    ids = request.form.getlist('ids[]')
    if not ids: flash('No users selected.', 'warning'); return redirect(url_for('admin.users'))
    for uid in ids:
        user = User.query.get(int(uid))
        if not user: continue
        if action == 'ban': user.is_banned = True; log_audit(admin, 'bulk_ban_user', 'user', uid)
        elif action == 'unban': user.is_banned = False; log_audit(admin, 'bulk_unban_user', 'user', uid)
        elif action == 'delete': db.session.delete(user); log_audit(admin, 'bulk_delete_user', 'user', uid)
    db.session.commit()
    flash(f'Bulk action "{action}" applied to {len(ids)} users.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:uid>/delete', methods=['POST'])
@require_admin('users')
def delete_user(admin, uid):
    user = User.query.get_or_404(uid)
    db.session.delete(user)
    db.session.commit()
    log_audit(admin, 'delete_user', 'user', uid, f'Deleted user account: {user.email or user.phone}')
    flash('User account deleted permanently.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:uid>')
@require_admin('users')
def user_detail(admin, uid):
    from models import User, Order, DeliveryAddress, UserLoginLog
    user = User.query.get_or_404(uid)
    orders = Order.query.filter_by(user_id=uid).order_by(Order.created_at.desc()).all()
    login_logs = UserLoginLog.query.filter_by(user_id=uid).order_by(UserLoginLog.timestamp.desc()).limit(50).all()
    return render_template('admin/user_detail.html', admin=admin, user=user, orders=orders, login_logs=login_logs)


# ── Inventory ────────────────────────────────────────────

@admin_bp.route('/inventory')
@require_admin('products')
def inventory(admin):
    from models import ProductVariant
    variants = ProductVariant.query.order_by(ProductVariant.stock.asc()).all()
    return render_template('admin/inventory.html', admin=admin, variants=variants)

@admin_bp.route('/inventory/update/<int:vid>', methods=['POST'])
@require_admin('products')
def update_stock(admin, vid):
    from models import ProductVariant
    variant = ProductVariant.query.get_or_404(vid)
    new_stock = int(request.form.get('stock', 0))
    old = variant.stock
    variant.stock = new_stock
    db.session.commit()
    log_audit(admin, 'update_stock', 'product_variant', vid, f'Stock updated {old} → {new_stock}')
    flash('Stock updated.', 'success')
    return redirect(url_for('admin.inventory'))


# ── Coupons ──────────────────────────────────────────────

@admin_bp.route('/coupons', methods=['GET', 'POST'])
@require_admin('orders')
def coupons(admin):
    from models import Coupon
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        if not code: flash('Code is required.', 'error'); return redirect(url_for('admin.coupons'))
        if Coupon.query.filter_by(code=code).first():
            flash('Coupon code already exists.', 'error'); return redirect(url_for('admin.coupons'))
        expires_str = request.form.get('expires_at', '')
        expires_at = datetime.strptime(expires_str, '%Y-%m-%d') if expires_str else None
        coupon = Coupon(
            code=code,
            discount_type=request.form.get('discount_type', 'percent'),
            value=float(request.form.get('value', 0)),
            max_uses=int(request.form.get('max_uses')) if request.form.get('max_uses') else None,
            min_order=float(request.form.get('min_order', 0)),
            expires_at=expires_at,
            is_active=True
        )
        db.session.add(coupon); db.session.commit()
        log_audit(admin, 'create_coupon', 'coupon', coupon.id, f'Created coupon {code}')
        flash(f'Coupon "{code}" created.', 'success')
        return redirect(url_for('admin.coupons'))

    all_coupons = Coupon.query.order_by(Coupon.created_at.desc()).all()
    return render_template('admin/coupons.html', admin=admin, coupons=all_coupons)

@admin_bp.route('/coupons/<int:cid>/toggle', methods=['POST'])
@require_admin('orders')
def toggle_coupon(admin, cid):
    from models import Coupon
    coupon = Coupon.query.get_or_404(cid)
    coupon.is_active = not coupon.is_active; db.session.commit()
    log_audit(admin, 'toggle_coupon', 'coupon', cid, f'Coupon {coupon.code} {"enabled" if coupon.is_active else "disabled"}')
    flash(f'Coupon {"enabled" if coupon.is_active else "disabled"}.', 'success')
    return redirect(url_for('admin.coupons'))

@admin_bp.route('/coupons/<int:cid>/delete', methods=['POST'])
@require_admin('orders')
def delete_coupon(admin, cid):
    from models import Coupon
    coupon = Coupon.query.get_or_404(cid)
    code = coupon.code; db.session.delete(coupon); db.session.commit()
    log_audit(admin, 'delete_coupon', 'coupon', cid, f'Deleted coupon {code}')
    flash(f'Coupon "{code}" deleted.', 'success')
    return redirect(url_for('admin.coupons'))


# ── API: validate coupon (used by cart JS) ─────────────

@admin_bp.route('/api/coupon/validate', methods=['POST'])
def api_validate_coupon():
    from models import Coupon
    code = request.json.get('code', '').strip().upper()
    coupon = Coupon.query.filter_by(code=code).first()
    if not coupon or not coupon.is_valid:
        return {'valid': False, 'message': 'Invalid or expired coupon.'}, 200
    return {'valid': True, 'discount_type': coupon.discount_type, 'value': coupon.value}, 200


# ── Settings ─────────────────────────────────────────────

@admin_bp.route('/settings', methods=['GET', 'POST'])
@require_admin('settings')
def settings(admin):
    from models import SiteSettings
    if request.method == 'POST':
        keys_to_save = ['site_name', 'support_email', 'maintenance_mode',
                        'meta_title', 'meta_description', 'meta_keywords']
        for key in keys_to_save:
            val = request.form.get(key, '')
            setting = SiteSettings.query.filter_by(key=key).first()
            if setting: setting.value = val
            else: db.session.add(SiteSettings(key=key, value=val))
        db.session.commit()
        log_audit(admin, 'update_settings', 'site_settings', None, 'Site settings updated')
        flash('Settings saved.', 'success')
        return redirect(url_for('admin.settings'))

    settings_map = {s.key: s.value for s in SiteSettings.query.all()}
    return render_template('admin/settings.html', admin=admin, settings=settings_map)


# ── Admin Team Management ────────────────────────────────

@admin_bp.route('/team', methods=['GET', 'POST'])
@require_admin('settings')
def team(admin):
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'support')
        if not username or not email or not password:
            flash('All fields required.', 'error')
            return redirect(url_for('admin.team'))
        if AdminUser.query.filter((AdminUser.email == email) | (AdminUser.username == username)).first():
            flash('Username or email already taken.', 'error')
            return redirect(url_for('admin.team'))
        import pyotp
        new_admin = AdminUser(username=username, email=email, role=role, totp_secret=pyotp.random_base32(), is_2fa_enabled=False)
        new_admin.set_password(password)
        db.session.add(new_admin); db.session.commit()
        log_audit(admin, 'create_admin', 'admin_user', new_admin.id, f'Created admin {username} ({role})')
        flash(f'Admin "{username}" created.', 'success')
        return redirect(url_for('admin.team'))

    all_admins = AdminUser.query.order_by(AdminUser.created_at.desc()).all()
    return render_template('admin/team.html', admin=admin, all_admins=all_admins, ADMIN_ROLES=ADMIN_ROLES)

@admin_bp.route('/team/<int:aid>/delete', methods=['POST'])
@require_admin('settings')
def delete_admin_member(admin, aid):
    if aid == admin.id: flash("You can't delete yourself.", 'error'); return redirect(url_for('admin.team'))
    target = AdminUser.query.get_or_404(aid)
    name = target.username; db.session.delete(target); db.session.commit()
    log_audit(admin, 'delete_admin', 'admin_user', aid, f'Deleted admin {name}')
    flash(f'Admin "{name}" deleted.', 'success')
    return redirect(url_for('admin.team'))

@admin_bp.route('/team/<int:aid>/lock', methods=['POST'])
@require_admin('settings')
def lock_admin_member(admin, aid):
    target = AdminUser.query.get_or_404(aid)
    target.is_locked = not target.is_locked; db.session.commit()
    action = 'lock_admin' if target.is_locked else 'unlock_admin'
    log_audit(admin, action, 'admin_user', aid, f'Admin {target.username} {"locked" if target.is_locked else "unlocked"}')
    flash(f'Admin {"locked" if target.is_locked else "unlocked"}.', 'success')
    return redirect(url_for('admin.team'))

@admin_bp.route('/team/<int:aid>/role', methods=['POST'])
@require_admin('settings')
def change_admin_role(admin, aid):
    target = AdminUser.query.get_or_404(aid)
    new_role = request.form.get('role', target.role)
    old_role = target.role; target.role = new_role; db.session.commit()
    log_audit(admin, 'change_admin_role', 'admin_user', aid, f'{target.username}: {old_role} → {new_role}')
    flash(f'Role changed to {new_role}.', 'success')
    return redirect(url_for('admin.team'))


# ── Orders (Enhanced bulk) ───────────────────────────────

@admin_bp.route('/orders/bulk', methods=['POST'])
@require_admin('orders')
def bulk_order_action(admin):
    from models import Order
    action = request.form.get('action')
    ids = request.form.getlist('ids[]')
    status_map = {'ship': 'Shipped', 'process': 'Processing', 'deliver': 'Delivered', 'cancel': 'Cancelled'}
    new_status = status_map.get(action)
    if new_status:
        for oid in ids:
            order = Order.query.get(int(oid))
            if order: order.status = new_status; log_audit(admin, f'bulk_{action}_order', 'order', oid)
        db.session.commit()
        flash(f'{len(ids)} orders marked as {new_status}.', 'success')
    return redirect(url_for('admin.orders'))

