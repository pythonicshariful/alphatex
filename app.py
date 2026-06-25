from flask import Flask
from config import Config
from extensions import db, login_manager, limiter, csrf
from models import User
import pyotp
from werkzeug.security import generate_password_hash

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Init extensions
    db.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from auth.routes import auth_bp
    from admin.routes import admin_bp
    from shop.routes import shop_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(shop_bp)

    with app.app_context():
        db.create_all()
        seed_db()

    return app

def seed_db():
    from models import Category, Product, AdminUser, User

    if not Category.query.first():
        cats = [
            Category(id='men', name='Menswear', image='men_category.jpg'),
            Category(id='women', name='Womenswear', image='women_category.jpg'),
            Category(id='accessories', name='Accessories', image='accessories_category.jpg'),
        ]
        db.session.add_all(cats)
        prods = [
            Product(name='Signature Platinum Thobe', price='$450.00', image='product_1.jpg', category_id='men', is_featured=True),
            Product(name='Luxury Silk Abaya', price='$620.00', image='product_2.jpg', category_id='women', is_featured=True),
            Product(name='Classic Leather Wallet', price='$150.00', image='product_3.jpg', category_id='accessories', is_featured=True),
            Product(name='Sahara Linen Panjabi', price='$280.00', image='product_4.jpg', category_id='men', is_featured=True),
            Product(name='Premium Co-Ord Set', price='$400.00', image='product_5.jpg', category_id='women', is_featured=False),
            Product(name='Oud Fragrance Collection', price='$320.00', image='product_6.jpg', category_id='accessories', is_featured=False),
        ]
        db.session.add_all(prods)
        db.session.commit()
        print('[Seed] Shop data seeded.')

    if not AdminUser.query.first():
        secret = pyotp.random_base32()
        admin = AdminUser(
            username='superadmin',
            email='admin@illiyeen.com',
            role='super_admin',
            totp_secret=secret,
            is_2fa_enabled=False,
        )
        admin.set_password('Admin@1234')
        db.session.add(admin)
        db.session.commit()
        print(f'[Seed] Super admin created: admin@illiyeen.com / Admin@1234')
        print(f'[Seed] TOTP Secret (for manual setup): {secret}')


app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
