from app import create_app
from extensions import db
from models import AdminUser
import pyotp

app = create_app()

with app.app_context():
    # Check if this admin already exists
    admin = AdminUser.query.filter_by(email='admin@admin.com').first()
    if not admin:
        secret = pyotp.random_base32()
        admin = AdminUser(
            username='admin',
            email='admin@admin.com',
            role='super_admin',
            totp_secret=secret,
            is_2fa_enabled=False,
        )
        admin.set_password('123456')
        db.session.add(admin)
        db.session.commit()
        print("New admin created! Email: admin@admin.com, Password: 123456")
    else:
        admin.set_password('123456')
        admin.is_2fa_enabled = False
        db.session.commit()
        print("Admin password reset! Email: admin@admin.com, Password: 123456")
