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
    is_banned = db.Column(db.Boolean, default=False)
    banned_reason = db.Column(db.String(500), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    last_login = db.Column(db.DateTime, nullable=True)
    social_provider = db.Column(db.String(50), nullable=True)  # 'google', 'facebook', None
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Extended profile fields
    full_name = db.Column(db.String(200), nullable=True)
    avatar = db.Column(db.String(200), nullable=True)           # filename stored under static/images/avatars/
    date_of_birth = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(20), nullable=True)            # 'male', 'female', 'other', 'prefer_not'
    alt_phone = db.Column(db.String(20), nullable=True)         # alternative mobile number
    profile_complete = db.Column(db.Boolean, default=False)     # True once user fills profile

    # Relationships
    addresses = db.relationship('DeliveryAddress', backref='user', lazy=True,
                                cascade='all, delete-orphan',
                                order_by='DeliveryAddress.is_default.desc()')
    wishlist_items = db.relationship('Wishlist', backref='user', lazy=True,
                                     cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def default_address(self):
        """Returns the user's default delivery address or the first one."""
        for addr in self.addresses:
            if addr.is_default:
                return addr
        return self.addresses[0] if self.addresses else None

    @property
    def display_name(self):
        """Best available display name for the user."""
        return self.full_name or self.username or (self.email.split('@')[0] if self.email else 'User')

    @property
    def avatar_url(self):
        """Returns a URL for the user's avatar, or a placeholder."""
        if self.avatar:
            return f'/static/images/avatars/{self.avatar}'
        return '/static/images/avatar_default.png'


class OTPRecord(db.Model):
    __tablename__ = 'otp_record'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), nullable=False)
    otp_hash = db.Column(db.String(256), nullable=False)
    purpose = db.Column(db.String(20), nullable=False)  # 'register', 'login', 'reset'
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ---------------------------------------------------------
# Shop Models
# ---------------------------------------------------------

class CarouselSlide(db.Model):
    __tablename__ = 'carousel_slide'
    id = db.Column(db.Integer, primary_key=True)
    image = db.Column(db.String(100), nullable=False)
    heading = db.Column(db.String(150), nullable=True)
    subheading = db.Column(db.String(250), nullable=True)
    button_text = db.Column(db.String(50), nullable=True)
    button_link = db.Column(db.String(250), nullable=True)
    order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)


class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(100), nullable=True)
    products = db.relationship('Product', backref='category', lazy=True)


class Offer(db.Model):
    __tablename__ = 'offer'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(150), unique=True, nullable=False)
    banner_image = db.Column(db.String(150), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    products = db.relationship('Product', backref='offer', lazy=True)


class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.String(50), nullable=False)
    compare_at_price = db.Column(db.String(50), nullable=True)
    image = db.Column(db.String(100), nullable=False)   # legacy single-image field (card thumbnail)
    category_id = db.Column(db.String(50), db.ForeignKey('category.id'), nullable=False)
    offer_id = db.Column(db.Integer, db.ForeignKey('offer.id'), nullable=True)
    is_featured = db.Column(db.Boolean, default=False)
    description = db.Column(db.Text, nullable=True)
    stock = db.Column(db.Integer, default=0, nullable=False)

    # ── SEO fields (auto-generated on save) ─────────────────────────────────
    slug = db.Column(db.String(220), unique=True, nullable=True, index=True)
    meta_title = db.Column(db.String(70), nullable=True)
    meta_description = db.Column(db.String(160), nullable=True)
    meta_keywords = db.Column(db.String(250), nullable=True)
    # ────────────────────────────────────────────────────────────────────────

    images = db.relationship('ProductImage', backref='product', lazy=True,
                             order_by='ProductImage.slot', cascade='all, delete-orphan')


    @property
    def hero_image(self):
        """Returns the slot-1 ProductImage or None."""
        return next((img for img in self.images if img.slot == 1), None)

    @property
    def gallery_images(self):
        """Returns slots 2-7."""
        return [img for img in self.images if img.slot > 1]


IMAGE_SLOT_LABELS = {
    1: ('Hero',        'Pure white BG, product fills 85% of frame'),
    2: ('Alternate',   'Back, side, or open/unboxed view'),
    3: ('Detail',      'Extreme close-up of key feature'),
    4: ('Lifestyle',   'Product in real-life setting'),
    5: ('Scale',       'Product next to hand / smartphone'),
    6: ('Infographic', 'Text overlays with specs & benefits'),
    7: ('In the Box',  'Everything the customer receives'),
}


class ProductImage(db.Model):
    __tablename__ = 'product_image'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    slot = db.Column(db.Integer, nullable=False)          # 1–7
    image_type = db.Column(db.String(30), nullable=False) # hero/alternate/detail/lifestyle/scale/infographic/box
    # Base filename without extension or size suffix, e.g. "p3_slot1"
    base_name = db.Column(db.String(150), nullable=False)
    alt_text = db.Column(db.String(255), nullable=True)
    # Tiny 20×20 base64 data URI for blur-up effect
    blur_data_uri = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def src(self, size=600):
        """Return URL path for a given width (300/600/1200/2000)."""
        return f'/static/images/products/{self.product_id}/{self.base_name}_{size}.webp'

    @property
    def srcset(self):
        return ', '.join(f'{self.src(w)} {w}w' for w in [300, 600, 1200, 2000])

    @property
    def src_fallback(self):
        return self.src(600)


# ---------------------------------------------------------
# Order & Variant Models
# ---------------------------------------------------------

class ProductVariant(db.Model):
    __tablename__ = 'product_variant'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    color = db.Column(db.String(50), nullable=True)
    size = db.Column(db.String(50), nullable=True)
    sku = db.Column(db.String(100), unique=True, nullable=True)
    stock = db.Column(db.Integer, default=0)
    image_id = db.Column(db.Integer, db.ForeignKey('product_image.id'), nullable=True)
    
    product = db.relationship('Product', backref=db.backref('variants', lazy=True, cascade='all, delete-orphan'))
    image = db.relationship('ProductImage')

class Order(db.Model):
    __tablename__ = 'order'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    status = db.Column(db.String(50), default='Pending')  # Pending, Processing, Shipped, Delivered, Cancelled
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    shipping_address = db.Column(db.Text, nullable=True)   # legacy plain-text fallback
    address_id = db.Column(db.Integer, db.ForeignKey('delivery_address.id'), nullable=True)  # structured FK
    tracking_number = db.Column(db.String(100), nullable=True)
    courier_name = db.Column(db.String(100), nullable=True)    # e.g. Pathao, RedX, Steadfast
    courier_tracking = db.Column(db.String(150), nullable=True)
    order_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('orders', lazy=True, cascade='all, delete-orphan'))
    delivery_address = db.relationship('DeliveryAddress', foreign_keys=[address_id])

class OrderItem(db.Model):
    __tablename__ = 'order_item'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey('product_variant.id'), nullable=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price_at_purchase = db.Column(db.Float, nullable=False)
    
    order = db.relationship('Order', backref=db.backref('items', lazy=True, cascade='all, delete-orphan'))
    product = db.relationship('Product')
    variant = db.relationship('ProductVariant')

    @property
    def price(self):
        return self.price_at_purchase

    @property
    def color(self):
        return self.variant.color if self.variant else None

    @property
    def size(self):
        return self.variant.size if self.variant else None


# ---------------------------------------------------------
# Delivery Address
# ---------------------------------------------------------

ADDRESS_LABELS = ['Home', 'Office', 'Other']

class DeliveryAddress(db.Model):
    """A saved delivery address belonging to a customer."""
    __tablename__ = 'delivery_address'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Recipient info
    recipient_name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20), nullable=False)

    # Bangladesh administrative divisions
    division = db.Column(db.String(100), nullable=False)
    district = db.Column(db.String(100), nullable=False)
    upazila = db.Column(db.String(100), nullable=False)
    union_ward = db.Column(db.String(100), nullable=True)   # optional

    # Street-level
    area = db.Column(db.String(200), nullable=True)             # Area / Locality / Mohalla
    road = db.Column(db.String(200), nullable=True)             # Road / Street
    house_no = db.Column(db.String(100), nullable=True)         # House / Holding No. (Optional)
    apartment = db.Column(db.String(100), nullable=True)        # Flat / Apartment
    postal_code = db.Column(db.String(10), nullable=True)

    # Extras
    delivery_instructions = db.Column(db.Text, nullable=True)
    maps_link = db.Column(db.String(500), nullable=True)        # Google Maps URL pasted by user
    label = db.Column(db.String(20), default='Home')            # Home, Office, Other
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def full_address(self):
        """Returns a single human-readable address string."""
        parts = [
            self.house_no,
            self.apartment,
            self.road,
            self.area,
            self.upazila,
            self.district,
            self.division,
            self.postal_code,
            'Bangladesh'
        ]
        return ', '.join(p for p in parts if p)


class Wishlist(db.Model):
    """Simple user wishlist — each row is one saved product."""
    __tablename__ = 'wishlist'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product')
    __table_args__ = (db.UniqueConstraint('user_id', 'product_id', name='uq_wishlist_user_product'),)


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


# ---------------------------------------------------------
# Security & Governance Models
# ---------------------------------------------------------

class AuditLog(db.Model):
    """Immutable log of admin actions. No update/delete routes permitted."""
    __tablename__ = 'audit_log'
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin_user.id'), nullable=True)
    admin_username = db.Column(db.String(150))       # denormalised for immutability
    action = db.Column(db.String(100), nullable=False) # e.g. 'ban_user', 'delete_product'
    target_type = db.Column(db.String(50), nullable=True)   # 'user', 'product', 'order'
    target_id = db.Column(db.String(50), nullable=True)
    details = db.Column(db.Text, nullable=True)       # human-readable detail string
    ip_address = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    admin = db.relationship('AdminUser', backref=db.backref('audit_logs', lazy=True))


class IPRule(db.Model):
    __tablename__ = 'ip_rule'
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(50), nullable=False, unique=True)
    rule_type = db.Column(db.String(20), nullable=False)  # 'whitelist' | 'blacklist'
    note = db.Column(db.String(250), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Coupon(db.Model):
    __tablename__ = 'coupon'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    discount_type = db.Column(db.String(20), nullable=False)  # 'percent' | 'fixed'
    value = db.Column(db.Float, nullable=False)
    max_uses = db.Column(db.Integer, nullable=True)   # None = unlimited
    uses = db.Column(db.Integer, default=0)
    min_order = db.Column(db.Float, default=0.0)
    expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_valid(self):
        if not self.is_active:
            return False
        if self.max_uses and self.uses >= self.max_uses:
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return True


class SiteSettings(db.Model):
    """Key-value store for site-wide configuration."""
    __tablename__ = 'site_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserLoginLog(db.Model):
    __tablename__ = 'user_login_log'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(256), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('login_logs', lazy=True, cascade='all, delete-orphan'))


class ProductViewLog(db.Model):
    __tablename__ = 'product_view_log'
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=False)
    category_id = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class NewsletterSubscriber(db.Model):
    __tablename__ = 'newsletter_subscriber'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    subscribed_at = db.Column(db.DateTime, default=datetime.utcnow)


class ContactMessage(db.Model):
    __tablename__ = 'contact_message'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(250), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='unread')  # 'unread' | 'read' | 'replied'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


