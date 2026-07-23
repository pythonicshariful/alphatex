from flask import Flask, render_template, jsonify, request
from config import Config
from extensions import db, login_manager, limiter, csrf, oauth
from models import User
from migrate import migrate_legacy_images
import pyotp
from werkzeug.security import generate_password_hash
from bot_protection import check_request

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Init extensions
    db.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    csrf.init_app(app)
    oauth.init_app(app)

    # Register OAuth providers
    oauth.register(
        name='google',
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
    oauth.register(
        name='facebook',
        api_base_url='https://graph.facebook.com/v16.0/',
        access_token_url='https://graph.facebook.com/v16.0/oauth/access_token',
        authorize_url='https://www.facebook.com/v16.0/dialog/oauth',
        client_kwargs={
            'scope': 'email public_profile'
        }
    )
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.before_request
    def bot_shield():
        """Bot protection — runs before every request."""
        # Skip static files to avoid blocking CSS/JS/images
        if request.path.startswith('/static/'):
            return
        return check_request()

    @app.before_request
    def check_banned_status():
        from flask_login import current_user, logout_user
        from flask import flash, redirect, url_for
        if current_user and current_user.is_authenticated:
            if getattr(current_user, 'is_banned', False):
                reason = getattr(current_user, 'banned_reason', 'Violation of terms')
                logout_user()
                flash(f'Your account has been restricted: {reason}', 'error')
                return redirect(url_for('auth.login'))

    @app.errorhandler(403)
    def forbidden(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Forbidden'}), 403
        return render_template('errors/403.html'), 403

    @app.errorhandler(429)
    def too_many_requests(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Too many requests. Please slow down.'}), 429
        return render_template('errors/429.html'), 429

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Not found'}), 404
        return render_template('errors/404.html'), 404

    # Register blueprints
    from auth.routes import auth_bp
    from admin.routes import admin_bp
    from shop.routes import shop_bp
    from user.routes import user_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(shop_bp)
    app.register_blueprint(user_bp)

    with app.app_context():
        # Drop old otp_record table if exists to migrate to email column schema
        try:
            db.session.execute(db.text("DROP TABLE IF EXISTS otp_record"))
            db.session.commit()
        except Exception as e:
            app.logger.error(f"Failed to drop otp_record: {e}")
            db.session.rollback()

        db.create_all()
        seed_db()
        migrate_legacy_images(app)

    @app.context_processor
    def inject_settings():
        from models import SiteSettings, Partner, Testimonial
        try:
            settings_map = {s.key: s.value for s in SiteSettings.query.all()}
        except Exception:
            settings_map = {}
        try:
            partners = Partner.query.filter_by(is_active=True).order_by(Partner.order).all()
        except Exception:
            partners = []
        try:
            testimonials = Testimonial.query.filter_by(is_active=True).order_by(Testimonial.order).all()
        except Exception:
            testimonials = []
        return {
            'site_settings': settings_map,
            'active_partners': partners,
            'active_testimonials': testimonials
        }

    @app.after_request
    def optimize_response(response):
        import gzip
        import io
        
        # 1. Caching rules for static assets (images, CSS, JS, fonts)
        if request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            # Only gzip compress textual static assets (skip compressed image formats)
            if any(request.path.endswith(ext) for ext in ['.css', '.js', '.svg']):
                response = gzip_response(response)
        else:
            # HTML pages and dynamic APIs: no-store but allow compression
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response = gzip_response(response)
            
        return response

    def gzip_response(res):
        import gzip
        import io
        accept_encoding = request.headers.get('Accept-Encoding', '')
        if 'gzip' not in accept_encoding.lower():
            return res
        if res.status_code < 200 or res.status_code >= 300:
            return res
        if 'Content-Encoding' in res.headers:
            return res
        ctype = res.headers.get('Content-Type', '').lower()
        if not any(t in ctype for t in ['text/html', 'text/css', 'application/javascript', 'application/json', 'image/svg+xml']):
            return res
        
        res.direct_passthrough = False
        data = res.get_data()
        if len(data) < 500:
            return res
            
        gzip_buffer = io.BytesIO()
        with gzip.GzipFile(mode='wb', fileobj=gzip_buffer) as gzip_file:
            gzip_file.write(data)
            
        res.set_data(gzip_buffer.getvalue())
        res.headers['Content-Encoding'] = 'gzip'
        res.headers['Content-Length'] = len(res.get_data())
        return res

    return app

def seed_db():
    from models import Category, Product, AdminUser, User, Partner, Testimonial

    if not Partner.query.first():
        partners = [
            Partner(name='Shwapno', image='partners/shwapno.webp', order=1),
            Partner(name='Unimart', image='partners/unimart.webp', order=2),
            Partner(name='Agora', image='partners/agora.webp', order=3),
            Partner(name='Meena Bazar', image='partners/meenabazar.webp', order=4),
            Partner(name='Khulshi Mart', image='partners/khulshimart.webp', order=5),
            Partner(name='Apon Family Mart', image='partners/aponfamilymart.webp', order=6),
            Partner(name='Lavender', image='partners/lavender.webp', order=7),
            Partner(name='The Basket', image='partners/thebasket.webp', order=8),
            Partner(name='Food Panda', image='partners/foodpanda.webp', order=9),
            Partner(name='Pathao', image='partners/pathao.webp', order=10),
        ]
        db.session.add_all(partners)
        db.session.commit()
        print('[Seed] Sales partners data seeded.')

    if not Testimonial.query.first():
        testimonials = [
            Testimonial(
                name='Zubair Rahman',
                content='The fabric quality of the Sahara Linen Panjabi is absolutely incredible. It feels soft and fits perfectly. Truly premium luxury fashion.',
                image='avatar_default.webp',
                rating=5,
                order=1
            ),
            Testimonial(
                name='Farhana Chowdhury',
                content='I ordered the Signature Platinum Thobe for my husband. The stitching details and the fall of the fabric are top-notch. Highly recommend!',
                image='avatar_default.webp',
                rating=5,
                order=2
            ),
            Testimonial(
                name='Adnan Sami',
                content='Excellent customer service! I needed to exchange sizes, and their styling concierge team resolved it within 24 hours. The new fit is perfect.',
                image='avatar_default.webp',
                rating=5,
                order=3
            )
        ]
        db.session.add_all(testimonials)
        db.session.commit()
        print('[Seed] Testimonials data seeded.')

    if not Category.query.first():
        cats = [
            Category(id='men', name='Menswear', image='men_category.webp'),
            Category(id='women', name='Womenswear', image='women_category.webp'),
            Category(id='accessories', name='Accessories', image='accessories_category.webp'),
        ]
        db.session.add_all(cats)
        prods = [
            Product(name='Signature Platinum Thobe', price='4500', image='product_1.jpg', category_id='men', is_featured=True),
            Product(name='Luxury Silk Abaya', price='6200', image='product_2.jpg', category_id='women', is_featured=True),
            Product(name='Classic Leather Wallet', price='1500', image='product_3.jpg', category_id='accessories', is_featured=True),
            Product(name='Sahara Linen Panjabi', price='2800', image='product_4.jpg', category_id='men', is_featured=True),
            Product(name='Premium Co-Ord Set', price='4000', image='product_5.jpg', category_id='women', is_featured=False),
            Product(name='Oud Fragrance Collection', price='3200', image='product_6.jpg', category_id='accessories', is_featured=False),
            Product(name='Embroidered Kurta Set', price='3500', image='product_1.jpg', category_id='men', is_featured=False, compare_at_price='4200'),
            Product(name='Designer Hijab Collection', price='1800', image='product_2.jpg', category_id='women', is_featured=True),
            Product(name='Premium Leather Belt', price='1200', image='product_3.jpg', category_id='accessories', is_featured=False),
            Product(name='Classic White Panjabi', price='2200', image='product_4.jpg', category_id='men', is_featured=False),
            Product(name='Elegant Maxi Dress', price='3800', image='product_5.jpg', category_id='women', is_featured=True, compare_at_price='4500'),
            Product(name='Premium Watch', price='5500', image='product_6.jpg', category_id='accessories', is_featured=True),
        ]
        db.session.add_all(prods)
        db.session.commit()
        print('[Seed] Shop data seeded.')

    # Ensure default super admins exist
    default_admins = [
        {'username': 'superadmin', 'email': 'alphatexsourcing5@gmail.com'},
        {'username': 'shariful_admin', 'email': 'pythonicshariful@gmail.com'}
    ]
    
    # Update legacy test@gmail.com admin if present
    legacy_admin = AdminUser.query.filter_by(email='test@gmail.com').first()
    if legacy_admin:
        legacy_admin.email = 'alphatexsourcing5@gmail.com'
        db.session.commit()

    for adm in default_admins:
        admin_rec = AdminUser.query.filter_by(email=adm['email']).first()
        if not admin_rec:
            uname = adm['username']
            if AdminUser.query.filter_by(username=uname).first():
                uname = f"{adm['username']}_sys"
            secret = pyotp.random_base32()
            admin_rec = AdminUser(
                username=uname,
                email=adm['email'],
                role='super_admin',
                totp_secret=secret,
                is_2fa_enabled=False,
            )
            db.session.add(admin_rec)
        admin_rec.role = 'super_admin'
        admin_rec.is_locked = False
        admin_rec.set_password('12345678')
        db.session.commit()
        print(f"[Seed] Super admin ready: {adm['email']} / Password: 12345678")


app = create_app()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5002, debug=False)
