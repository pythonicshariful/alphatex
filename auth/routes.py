import re
import hashlib
import random
import string
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db, limiter
from models import User, OTPRecord

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

BD_PHONE_RE = re.compile(r'^\+8801[3-9]\d{8}$')


# -------------------------------------------------------
# OTP Utilities
# -------------------------------------------------------

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def hash_otp(otp):
    return hashlib.sha256(otp.encode()).hexdigest()

def send_otp_sms(phone, otp):
    """Tries Twilio; falls back to console mock."""
    from flask import current_app
    sid = current_app.config.get('TWILIO_ACCOUNT_SID')
    token = current_app.config.get('TWILIO_AUTH_TOKEN')
    from_number = current_app.config.get('TWILIO_PHONE_NUMBER')
    if sid and token and from_number:
        try:
            from twilio.rest import Client
            client = Client(sid, token)
            client.messages.create(body=f'Your ILLIYEEN OTP is: {otp}', from_=from_number, to=phone)
            return True
        except Exception as e:
            current_app.logger.error(f'Twilio error: {e}')
    # Console mock
    print(f'\n[OTP MOCK] Phone: {phone} -> OTP: {otp}\n', flush=True)
    return True

def create_otp_record(phone, purpose):
    # Invalidate old OTPs for same phone+purpose
    OTPRecord.query.filter_by(phone=phone, purpose=purpose, used=False).update({'used': True})
    otp = generate_otp()
    record = OTPRecord(
        phone=phone,
        otp_hash=hash_otp(otp),
        purpose=purpose,
        expires_at=datetime.utcnow() + timedelta(minutes=10)
    )
    db.session.add(record)
    db.session.commit()
    return otp

def verify_otp_record(phone, otp, purpose):
    record = OTPRecord.query.filter_by(
        phone=phone, purpose=purpose, used=False
    ).order_by(OTPRecord.created_at.desc()).first()
    if not record:
        return False, 'No OTP found. Please request a new one.'
    if record.expires_at < datetime.utcnow():
        return False, 'OTP has expired. Please request a new one.'
    if record.otp_hash != hash_otp(otp):
        return False, 'Invalid OTP. Please try again.'
    record.used = True
    db.session.commit()
    return True, 'OTP verified successfully.'


# -------------------------------------------------------
# Customer Registration (Step-by-step)
# -------------------------------------------------------

@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit('20/hour')
def register():
    if current_user.is_authenticated:
        return redirect(url_for('shop.index'))
    return render_template('auth/register.html')


@auth_bp.route('/register/send-otp', methods=['POST'])
@limiter.limit('3/hour', key_func=lambda: request.form.get('phone', ''))
def register_send_otp():
    raw = request.form.get('phone', '').strip()
    # Prepend +88 if user typed just the local part (starting with 0)
    phone = '+88' + raw if not raw.startswith('+') else raw
    if not BD_PHONE_RE.match(phone):
        flash('Please enter a valid Bangladeshi mobile number (e.g. +8801XXXXXXXXX).', 'error')
        return redirect(url_for('auth.register'))
    existing = User.query.filter_by(phone=phone).first()
    if existing and existing.is_verified:
        flash('This number is already registered. Please log in.', 'error')
        return redirect(url_for('auth.login'))
    otp = create_otp_record(phone, 'register')
    send_otp_sms(phone, otp)
    session['reg_phone'] = phone
    flash('OTP sent to your mobile number!', 'success')
    return redirect(url_for('auth.register_verify'))


@auth_bp.route('/register/verify', methods=['GET', 'POST'])
def register_verify():
    phone = session.get('reg_phone')
    if not phone:
        return redirect(url_for('auth.register'))
    if request.method == 'POST':
        otp = request.form.get('otp', '').strip()
        ok, msg = verify_otp_record(phone, otp, 'register')
        if not ok:
            flash(msg, 'error')
            return render_template('auth/otp_verify.html', phone=phone, purpose='register')
        session['reg_phone_verified'] = phone
        return redirect(url_for('auth.register_set_password'))
    return render_template('auth/otp_verify.html', phone=phone, purpose='register')


@auth_bp.route('/register/set-password', methods=['GET', 'POST'])
def register_set_password():
    phone = session.get('reg_phone_verified')
    if not phone:
        return redirect(url_for('auth.register'))
    if request.method == 'POST':
        password = request.form.get('password', '')
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('auth/set_password.html', phone=phone)
        user = User.query.filter_by(phone=phone).first()
        if not user:
            user = User(phone=phone)
        user.set_password(password)
        user.is_verified = True
        db.session.add(user)
        db.session.commit()
        login_user(user, remember=True)
        session.pop('reg_phone', None)
        session.pop('reg_phone_verified', None)
        flash('Welcome to ILLIYEEN! Your account has been created.', 'success')
        return redirect(url_for('auth.add_email'))
    return render_template('auth/set_password.html', phone=phone)


@auth_bp.route('/register/add-email', methods=['GET', 'POST'])
@login_required
def add_email():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if email:
            current_user.email = email
            db.session.commit()
        return redirect(url_for('shop.index'))
    return render_template('auth/add_email.html')


# -------------------------------------------------------
# Customer Login
# -------------------------------------------------------

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('shop.index'))
    return render_template('auth/login.html')


@auth_bp.route('/login/password', methods=['POST'])
@limiter.limit('10/minute')
def login_password():
    identifier = request.form.get('identifier', '').strip()
    password = request.form.get('password', '')
    remember = bool(request.form.get('remember'))
    user = User.query.filter(
        (User.phone == identifier) | (User.email == identifier)
    ).first()
    if user and user.check_password(password):
        login_user(user, remember=remember)
        return redirect(url_for('shop.index'))
    flash('Invalid credentials. Please try again.', 'error')
    return redirect(url_for('auth.login'))


@auth_bp.route('/login/send-otp', methods=['POST'])
@limiter.limit('3/hour', key_func=lambda: request.form.get('phone', ''))
def login_send_otp():
    raw = request.form.get('phone', '').strip()
    phone = '+88' + raw if not raw.startswith('+') else raw
    if not BD_PHONE_RE.match(phone):
        flash('Please enter a valid Bangladeshi mobile number.', 'error')
        return redirect(url_for('auth.login'))
    user = User.query.filter_by(phone=phone, is_verified=True).first()
    if not user:
        flash('No verified account found with this number. Please register first.', 'error')
        return redirect(url_for('auth.login'))
    otp = create_otp_record(phone, 'login')
    send_otp_sms(phone, otp)
    session['login_phone'] = phone
    return redirect(url_for('auth.login_verify'))


@auth_bp.route('/login/verify', methods=['GET', 'POST'])
def login_verify():
    phone = session.get('login_phone')
    if not phone:
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        otp = request.form.get('otp', '').strip()
        remember = bool(request.form.get('remember'))
        ok, msg = verify_otp_record(phone, otp, 'login')
        if not ok:
            flash(msg, 'error')
            return render_template('auth/otp_verify.html', phone=phone, purpose='login', remember=remember)
        user = User.query.filter_by(phone=phone).first()
        login_user(user, remember=remember)
        session.pop('login_phone', None)
        return redirect(url_for('shop.index'))
    return render_template('auth/otp_verify.html', phone=phone, purpose='login')


# -------------------------------------------------------
# Password Reset
# -------------------------------------------------------

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_request():
    if request.method == 'POST':
        raw = request.form.get('phone', '').strip()
        phone = '+88' + raw if not raw.startswith('+') else raw
        user = User.query.filter_by(phone=phone, is_verified=True).first()
        if user:
            otp = create_otp_record(phone, 'reset')
            send_otp_sms(phone, otp)
            session['reset_phone'] = phone
            return redirect(url_for('auth.reset_verify'))
        flash('No account found with that number.', 'error')
    return render_template('auth/reset_request.html')


@auth_bp.route('/reset-password/verify', methods=['GET', 'POST'])
def reset_verify():
    phone = session.get('reset_phone')
    if not phone:
        return redirect(url_for('auth.reset_request'))
    if request.method == 'POST':
        otp = request.form.get('otp', '').strip()
        ok, msg = verify_otp_record(phone, otp, 'reset')
        if not ok:
            flash(msg, 'error')
            return render_template('auth/otp_verify.html', phone=phone, purpose='reset')
        session['reset_phone_verified'] = phone
        return redirect(url_for('auth.reset_set_password'))
    return render_template('auth/otp_verify.html', phone=phone, purpose='reset')


@auth_bp.route('/reset-password/set', methods=['GET', 'POST'])
def reset_set_password():
    phone = session.get('reset_phone_verified')
    if not phone:
        return redirect(url_for('auth.reset_request'))
    if request.method == 'POST':
        password = request.form.get('password', '')
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('auth/set_password.html', phone=phone, mode='reset')
        user = User.query.filter_by(phone=phone).first()
        user.set_password(password)
        db.session.commit()
        session.pop('reset_phone', None)
        session.pop('reset_phone_verified', None)
        flash('Password updated! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/set_password.html', phone=phone, mode='reset')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('shop.index'))
