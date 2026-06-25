from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pyotp

# ---------------------------------------------------------
# Customer Models
# ---------------------------------------------------------

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    email = db.Column(db.String(150), unique=True, nullable=True)
    username = db.Column(db.String(150), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    is_guest = db.Column(db.Boolean, default=False)
    social_provider = db.Column(db.String(50), nullable=True)  # 'google', 'facebook', None
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class OTPRecord(db.Model):
    __tablename__ = 'otp_record'
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), nullable=False)
    otp_hash = db.Column(db.String(256), nullable=False)
    purpose = db.Column(db.String(20), nullable=False)  # 'register', 'login', 'reset'
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ---------------------------------------------------------
# Shop Models
# ---------------------------------------------------------

class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(100), nullable=False)
    products = db.relationship('Product', backref='category', lazy=True)


class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.String(50), db.ForeignKey('category.id'), nullable=False)
    is_featured = db.Column(db.Boolean, default=False)


# ---------------------------------------------------------
# Admin Models
# ---------------------------------------------------------

ADMIN_ROLES = {
    'super_admin':      ['products', 'categories', 'orders', 'users', 'settings', 'logs'],
    'order_manager':    ['orders'],
    'content_uploader': ['products', 'categories'],
    'support':          ['users', 'orders'],
}


class AdminUser(db.Model):
    __tablename__ = 'admin_user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='support')  # see ADMIN_ROLES
    totp_secret = db.Column(db.String(64), nullable=True)
    is_2fa_enabled = db.Column(db.Boolean, default=False)
    is_locked = db.Column(db.Boolean, default=False)
    failed_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    login_logs = db.relationship('AdminLoginLog', backref='admin', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_totp_uri(self):
        return pyotp.totp.TOTP(self.totp_secret).provisioning_uri(
            name=self.email, issuer_name='ILLIYEEN Admin'
        )

    def verify_totp(self, code):
        totp = pyotp.TOTP(self.totp_secret)
        return totp.verify(code, valid_window=1)

    @property
    def permissions(self):
        return ADMIN_ROLES.get(self.role, [])

    def has_permission(self, module):
        return module in self.permissions


class AdminLoginLog(db.Model):
    __tablename__ = 'admin_login_log'
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin_user.id'), nullable=True)
    email = db.Column(db.String(150))
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(250))
    status = db.Column(db.String(20))   # 'success', 'fail_password', 'fail_2fa', 'locked'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
