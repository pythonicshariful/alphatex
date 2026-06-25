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
from models import AdminUser, AdminLoginLog, ADMIN_ROLES, Category, Product, User, CarouselSlide, ProductImage

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

        # Credentials valid — proceed to 2FA
        admin.failed_attempts = 0
        db.session.commit()
        session['admin_pending_id'] = admin.id
        if admin.is_2fa_enabled:
            return redirect(url_for('admin.two_factor'))
        else:
            # First login: force 2FA setup
            return redirect(url_for('admin.setup_2fa'))
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
    stats = {
        'products': Product.query.count(),
        'categories': Category.query.count(),
        'users': User.query.count(),
        'admins': AdminUser.query.count(),
    }
    return render_template('admin/dashboard.html', admin=admin, stats=stats,
                           ADMIN_ROLES=ADMIN_ROLES)


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
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        category_id = request.form.get('category_id')
        is_featured = bool(request.form.get('is_featured'))
        description = request.form.get('description', '')
        
        # Legacy fallback image just in case
        legacy_image = request.form.get('image', 'product_1.jpg')

        p = Product(name=name, price=price, image=legacy_image,
                    category_id=category_id, is_featured=is_featured, description=description)
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
                    
        db.session.commit()
        flash(f'Product "{name}" added successfully.', 'success')
        return redirect(url_for('admin.products'))
        
    return render_template('admin/product_form.html', admin=admin, categories=categories, product=None)


@admin_bp.route('/products/edit/<int:pid>', methods=['GET', 'POST'])
@require_admin('products')
def edit_product(admin, pid):
    p = Product.query.get_or_404(pid)
    categories = Category.query.all()
    
    if request.method == 'POST':
        p.name = request.form.get('name')
        p.price = request.form.get('price')
        p.category_id = request.form.get('category_id')
        p.is_featured = bool(request.form.get('is_featured'))
        p.description = request.form.get('description', '')
        
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
                    
        db.session.commit()
        flash('Product updated successfully.', 'success')
        return redirect(url_for('admin.products'))
        
    return render_template('admin/product_form.html', admin=admin, categories=categories, product=p)


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
        
        if file and file.filename:
            filename = secure_filename(file.filename)
            upload_dir = os.path.join(current_app.root_path, 'static', 'images', 'carousel')
            os.makedirs(upload_dir, exist_ok=True)
            filepath = os.path.join(upload_dir, filename)
            file.save(filepath)
            
            slide = CarouselSlide(
                image=f"/static/images/carousel/{filename}",
                heading=heading,
                subheading=subheading,
                button_text=button_text,
                button_link=button_link
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


@admin_bp.route('/users')
@require_admin('users')
def users(admin):
    users = User.query.all()
    return render_template('admin/users.html', admin=admin, users=users)

@admin_bp.route('/login-history')
@require_admin('logs')
def login_history(admin):
    logs = AdminLoginLog.query.order_by(AdminLoginLog.timestamp.desc()).limit(200).all()
    return render_template('admin/login_history.html', admin=admin, logs=logs)
