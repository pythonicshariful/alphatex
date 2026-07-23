import re
import hashlib
import random
import string
import requests
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db, limiter
from models import User, OTPRecord
from utils.mail import send_otp_email

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

BD_PHONE_RE = re.compile(r'^\+8801[3-9]\d{8}$')

def verify_turnstile(token):
    secret = current_app.config.get('TURNSTILE_SECRET_KEY')
    if not secret:
        return True
    if not token:
        return False
    data = {
        'secret': secret,
        'response': token
    }
    try:
        res = requests.post('https://challenges.cloudflare.com/turnstile/v0/siteverify', data=data)
        return res.json().get('success', False)
    except Exception as e:
        current_app.logger.error(f"Turnstile error: {e}")
        return False


def log_user_login(user):
    from models import UserLoginLog
    try:
        log = UserLoginLog(
            user_id=user.id,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string if request.user_agent else None
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Failed to log user login: {e}")

# -------------------------------------------------------
# OTP Utilities
# -------------------------------------------------------

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def hash_otp(otp):
    return hashlib.sha256(otp.encode()).hexdigest()

def create_otp_record(email, purpose):
    # Invalidate old OTPs for same email+purpose
    OTPRecord.query.filter_by(email=email, purpose=purpose, used=False).update({'used': True})
    otp = generate_otp()
    record = OTPRecord(
        email=email,
        otp_hash=hash_otp(otp),
        purpose=purpose,
        expires_at=datetime.utcnow() + timedelta(minutes=10)
    )
    db.session.add(record)
    db.session.commit()
    return otp

def verify_otp_record(email, otp, purpose):
    record = OTPRecord.query.filter_by(
        email=email, purpose=purpose, used=False
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
@auth_bp.route('/register/send-otp', methods=['POST'])
@limiter.limit('3/hour', key_func=lambda: request.form.get('email', ''))
def register_send_otp():
    from bot_protection import verify_captcha
    if not verify_captcha(form_type='register'):
        flash('Security check / Captcha failed. Please try again.', 'error')
        return redirect(url_for('auth.register'))
        
    email = request.form.get('email', '').strip().lower()
    if not email or not re.match(r'[^@]+@[^@]+\.[^@]+', email):
        flash('Please enter a valid email address.', 'error')
        return redirect(url_for('auth.register'))
    existing = User.query.filter_by(email=email).first()
    if existing and existing.is_verified:
        flash('This email is already registered. Please log in.', 'error')
        return redirect(url_for('auth.login'))
    otp = create_otp_record(email, 'register')
    send_otp_email(email, otp)
    session['reg_email'] = email
    flash('OTP sent to your email address!', 'success')
    return redirect(url_for('auth.register_verify'))


@auth_bp.route('/register/verify', methods=['GET', 'POST'])
def register_verify():
    email = session.get('reg_email')
    if not email:
        return redirect(url_for('auth.register'))
    if request.method == 'POST':
        otp = request.form.get('otp', '').strip()
        ok, msg = verify_otp_record(email, otp, 'register')
        if not ok:
            flash(msg, 'error')
            return render_template('auth/otp_verify.html', email=email, purpose='register')
        session['reg_email_verified'] = email
        return redirect(url_for('auth.register_set_password'))
    return render_template('auth/otp_verify.html', email=email, purpose='register')


@auth_bp.route('/register/set-password', methods=['GET', 'POST'])
def register_set_password():
    email = session.get('reg_email_verified')
    if not email:
        return redirect(url_for('auth.register'))
    if request.method == 'POST':
        password = request.form.get('password', '')
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('auth/set_password.html', email=email)
        user = User.query.filter_by(email=email).first()
        if not user:
            base_username = email.split('@')[0]
            username = base_username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1
            user = User(email=email, username=username)
        user.set_password(password)
        user.is_verified = True
        db.session.add(user)
        db.session.commit()
        login_user(user, remember=True)
        log_user_login(user)
        session.pop('reg_email', None)
        session.pop('reg_email_verified', None)
        flash('Welcome to alphatex! Your account has been created.', 'success')
        return redirect(url_for('shop.index'))
    return render_template('auth/set_password.html', email=email)


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
    from bot_protection import verify_captcha
    if not verify_captcha(form_type='login'):
        flash('Security check / Captcha failed. Please try again.', 'error')
        return redirect(url_for('auth.login'))
        
    identifier = request.form.get('identifier', '').strip()
    password = request.form.get('password', '')
    remember = bool(request.form.get('remember'))
    user = User.query.filter(
        (User.phone == identifier) | (User.email == identifier)
    ).first()
    if user and user.check_password(password):
        login_user(user, remember=remember)
        log_user_login(user)
        return redirect(url_for('shop.index'))
    flash('Invalid credentials. Please try again.', 'error')
    return redirect(url_for('auth.login'))


@auth_bp.route('/login/send-otp', methods=['POST'])
@limiter.limit('3/hour', key_func=lambda: request.form.get('email', ''))
def login_send_otp():
    from bot_protection import verify_captcha
    if not verify_captcha(form_type='login'):
        flash('Security check / Captcha failed. Please try again.', 'error')
        return redirect(url_for('auth.login'))
        
    email = request.form.get('email', '').strip().lower()
    if not email:
        flash('Please enter a valid email address.', 'error')
        return redirect(url_for('auth.login'))
    user = User.query.filter_by(email=email, is_verified=True).first()
    if not user:
        flash('No verified account found with this email. Please register first.', 'error')
        return redirect(url_for('auth.login'))
    otp = create_otp_record(email, 'login')
    send_otp_email(email, otp)
    session['login_email'] = email
    return redirect(url_for('auth.login_verify'))


@auth_bp.route('/login/verify', methods=['GET', 'POST'])
def login_verify():
    email = session.get('login_email')
    if not email:
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        otp = request.form.get('otp', '').strip()
        remember = bool(request.form.get('remember'))
        ok, msg = verify_otp_record(email, otp, 'login')
        if not ok:
            flash(msg, 'error')
            return render_template('auth/otp_verify.html', email=email, purpose='login', remember=remember)
        user = User.query.filter_by(email=email).first()
        login_user(user, remember=remember)
        log_user_login(user)
        session.pop('login_email', None)
        return redirect(url_for('shop.index'))
    return render_template('auth/otp_verify.html', email=email, purpose='login')


# -------------------------------------------------------
# Password Reset
# -------------------------------------------------------

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_request():
    if request.method == 'POST':
        from bot_protection import verify_captcha
        if not verify_captcha(form_type='login'):
            flash('Security check / Captcha failed. Please try again.', 'error')
            return redirect(url_for('auth.reset_request'))
            
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email, is_verified=True).first()
        if user:
            otp = create_otp_record(email, 'reset')
            send_otp_email(email, otp)
            session['reset_email'] = email
            return redirect(url_for('auth.reset_verify'))
        flash('No account found with that email address.', 'error')
    return render_template('auth/reset_request.html')


@auth_bp.route('/reset-password/verify', methods=['GET', 'POST'])
def reset_verify():
    email = session.get('reset_email')
    if not email:
        return redirect(url_for('auth.reset_request'))
    if request.method == 'POST':
        otp = request.form.get('otp', '').strip()
        ok, msg = verify_otp_record(email, otp, 'reset')
        if not ok:
            flash(msg, 'error')
            return render_template('auth/otp_verify.html', email=email, purpose='reset')
        session['reset_email_verified'] = email
        return redirect(url_for('auth.reset_set_password'))
    return render_template('auth/otp_verify.html', email=email, purpose='reset')


@auth_bp.route('/reset-password/set', methods=['GET', 'POST'])
def reset_set_password():
    email = session.get('reset_email_verified')
    if not email:
        return redirect(url_for('auth.reset_request'))
    if request.method == 'POST':
        password = request.form.get('password', '')
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('auth/set_password.html', email=email, mode='reset')
        user = User.query.filter_by(email=email).first()
        user.set_password(password)
        db.session.commit()
        session.pop('reset_email', None)
        session.pop('reset_email_verified', None)
        flash('Password updated! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/set_password.html', email=email, mode='reset')


# -------------------------------------------------------
# Social Login
# -------------------------------------------------------

def get_google_oauth():
    from models import SiteSettings
    from extensions import oauth
    enabled = SiteSettings.query.filter_by(key='google_login_enabled').first()
    if enabled and enabled.value != 'true':
        return None, "Google login is currently disabled by administrator."
    
    cid = SiteSettings.query.filter_by(key='google_client_id').first()
    csecret = SiteSettings.query.filter_by(key='google_client_secret').first()
    
    client_id = (cid.value if cid and cid.value else current_app.config.get('GOOGLE_CLIENT_ID', '') or '').strip()
    client_secret = (csecret.value if csecret and csecret.value else current_app.config.get('GOOGLE_CLIENT_SECRET', '') or '').strip()

    if not client_id or not client_secret:
        return None, "Google Client ID or Secret is not configured in Admin Dashboard."

    oauth.google.client_id = client_id
    oauth.google.client_secret = client_secret
    return oauth.google, None


def get_facebook_oauth():
    from models import SiteSettings
    from extensions import oauth
    enabled = SiteSettings.query.filter_by(key='facebook_login_enabled').first()
    if enabled and enabled.value != 'true':
        return None, "Facebook login is currently disabled by administrator."

    appid = SiteSettings.query.filter_by(key='facebook_app_id').first()
    appsecret = SiteSettings.query.filter_by(key='facebook_app_secret').first()

    client_id = (appid.value if appid and appid.value else current_app.config.get('FACEBOOK_CLIENT_ID', '') or '').strip()
    client_secret = (appsecret.value if appsecret and appsecret.value else current_app.config.get('FACEBOOK_CLIENT_SECRET', '') or '').strip()

    if not client_id or not client_secret:
        return None, "Facebook App ID or Secret is not configured in Admin Dashboard."

    oauth.facebook.client_id = client_id
    oauth.facebook.client_secret = client_secret
    return oauth.facebook, None


@auth_bp.route('/login/google')
def google_login():
    google, err = get_google_oauth()
    if not google:
        flash(err, 'error')
        return redirect(url_for('auth.login'))
    redirect_uri = url_for('auth.google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@auth_bp.route('/callback/google')
def google_callback():
    google, err = get_google_oauth()
    if not google:
        flash(err, 'error')
        return redirect(url_for('auth.login'))
    
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')
        if not user_info:
            flash('Failed to fetch user info from Google.', 'error')
            return redirect(url_for('auth.login'))
    except Exception as e:
        current_app.logger.error(f"Google Callback error: {e}")
        flash('Google login error. Please try again.', 'error')
        return redirect(url_for('auth.login'))
    
    email = user_info.get('email')
    user = User.query.filter_by(email=email).first()
    if not user:
        full_name = user_info.get('name')
        user = User(email=email, social_provider='google', is_verified=True, 
                    username=email.split('@')[0], full_name=full_name)
        db.session.add(user)
        db.session.commit()
    else:
        user.social_provider = 'google'
        user.is_verified = True
        db.session.commit()
    
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    login_user(user, remember=True)
    log_user_login(user)
    
    if not user.profile_complete:
        flash('Welcome! Please complete your profile to enable seamless checkouts and delivery.', 'info')
        return redirect(url_for('user.profile'))
        
    return redirect(url_for('shop.index'))


@auth_bp.route('/login/facebook')
def facebook_login():
    facebook, err = get_facebook_oauth()
    if not facebook:
        flash(err, 'error')
        return redirect(url_for('auth.login'))
    redirect_uri = url_for('auth.facebook_callback', _external=True)
    return facebook.authorize_redirect(redirect_uri)

@auth_bp.route('/callback/facebook')
def facebook_callback():
    facebook, err = get_facebook_oauth()
    if not facebook:
        flash(err, 'error')
        return redirect(url_for('auth.login'))
    
    try:
        token = facebook.authorize_access_token()
        resp = facebook.get('me?fields=id,name,email')
        user_info = resp.json()
        if not user_info.get('email'):
            flash('Failed to fetch email from Facebook.', 'error')
            return redirect(url_for('auth.login'))
    except Exception as e:
        current_app.logger.error(f"Facebook Callback error: {e}")
        flash('Facebook login error. Please try again.', 'error')
        return redirect(url_for('auth.login'))
    
    email = user_info.get('email')
    user = User.query.filter_by(email=email).first()
    if not user:
        full_name = user_info.get('name')
        user = User(email=email, social_provider='facebook', is_verified=True, 
                    username=email.split('@')[0], full_name=full_name)
        db.session.add(user)
        db.session.commit()
    else:
        user.social_provider = 'facebook'
        user.is_verified = True
        db.session.commit()
    
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    login_user(user, remember=True)
    log_user_login(user)
    
    if not user.profile_complete:
        flash('Welcome! Please complete your profile to enable seamless checkouts and delivery.', 'info')
        return redirect(url_for('user.profile'))
        
    return redirect(url_for('shop.index'))


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('shop.index'))
