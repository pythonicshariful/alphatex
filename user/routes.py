import os
import re
from datetime import datetime
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, current_app, jsonify)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from extensions import db
from models import DeliveryAddress, Order, Wishlist, ADDRESS_LABELS

user_bp = Blueprint('user', __name__, url_prefix='/account')

BD_PHONE_RE = re.compile(r'^\+?8?8?01[3-9]\d{8}$')
ALLOWED_AVATAR_EXT = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB


def _allowed_avatar(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_AVATAR_EXT


def _normalise_phone(raw):
    """Ensure phone number is stored in +8801XXXXXXXXX format."""
    raw = raw.strip()
    if raw.startswith('01') and len(raw) == 11:
        return '+88' + raw
    if raw.startswith('8801') and len(raw) == 13:
        return '+' + raw
    return raw


# -------------------------------------------------------
# Dashboard
# -------------------------------------------------------

@user_bp.route('/')
@login_required
def dashboard():
    recent_orders = Order.query.filter_by(user_id=current_user.id)\
                               .order_by(Order.created_at.desc()).limit(5).all()
    addr_count = DeliveryAddress.query.filter_by(user_id=current_user.id).count()
    wishlist_count = Wishlist.query.filter_by(user_id=current_user.id).count()

    # Profile completion percentage
    steps = [
        bool(current_user.full_name),
        bool(current_user.phone),
        bool(current_user.avatar),
        bool(current_user.date_of_birth),
        bool(addr_count),
    ]
    completion = int((sum(steps) / len(steps)) * 100)

    return render_template('user/dashboard.html',
                           recent_orders=recent_orders,
                           addr_count=addr_count,
                           wishlist_count=wishlist_count,
                           completion=completion)


# -------------------------------------------------------
# Profile
# -------------------------------------------------------

@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        gender = request.form.get('gender', '').strip()
        dob_str = request.form.get('date_of_birth', '').strip()
        phone = request.form.get('phone', '').strip()
        alt_phone = request.form.get('alt_phone', '').strip()

        if full_name:
            current_user.full_name = full_name
        if gender:
            current_user.gender = gender
        if dob_str:
            try:
                from datetime import date
                current_user.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date of birth format.', 'error')
                return redirect(url_for('user.profile'))
        
        if phone and not current_user.phone:
            norm = _normalise_phone(phone)
            if not BD_PHONE_RE.match(norm):
                flash('Please enter a valid Bangladeshi mobile number (e.g. 01XXXXXXXXX).', 'error')
                return redirect(url_for('user.profile'))
            from models import User
            existing = User.query.filter(User.phone == norm, User.id != current_user.id).first()
            if existing:
                flash('This mobile number is already registered to another account.', 'error')
                return redirect(url_for('user.profile'))
            current_user.phone = norm

        if alt_phone:
            norm = _normalise_phone(alt_phone)
            current_user.alt_phone = norm

        # Mark profile complete if key fields are filled
        if current_user.full_name and current_user.phone:
            current_user.profile_complete = True

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('user.profile'))

    return render_template('user/profile.html')


@user_bp.route('/avatar/upload', methods=['POST'])
@login_required
def avatar_upload():
    """AJAX endpoint: accept avatar file, save, return new URL."""
    file = request.files.get('avatar')
    if not file or file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    if not _allowed_avatar(file.filename):
        return jsonify({'error': 'File type not allowed. Use JPG, PNG, WebP or GIF.'}), 400

    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_AVATAR_SIZE:
        return jsonify({'error': 'File too large. Maximum 5 MB.'}), 400

    avatars_dir = os.path.join(current_app.root_path, 'static', 'images', 'avatars')
    filename_base = f'user_{current_user.id}'
    
    from utils.images import optimize_and_save_image
    saved_filename = optimize_and_save_image(file, avatars_dir, filename_base, max_width=300)

    current_user.avatar = saved_filename
    db.session.commit()
    return jsonify({'url': f'/static/images/avatars/{saved_filename}', 'success': True})


# -------------------------------------------------------
# Delivery Addresses
# -------------------------------------------------------

@user_bp.route('/addresses')
@login_required
def addresses():
    addrs = DeliveryAddress.query.filter_by(user_id=current_user.id)\
                                 .order_by(DeliveryAddress.is_default.desc(),
                                           DeliveryAddress.created_at.desc()).all()
    return render_template('user/addresses.html', addresses=addrs, labels=ADDRESS_LABELS)


@user_bp.route('/addresses/add', methods=['GET', 'POST'])
@login_required
def address_add():
    if request.method == 'POST':
        err = _save_address(None)
        if err:
            flash(err, 'error')
            return redirect(url_for('user.address_add'))
        flash('Address saved!', 'success')
        return redirect(url_for('user.addresses'))
    return render_template('user/address_form.html', address=None, labels=ADDRESS_LABELS)


@user_bp.route('/addresses/<int:addr_id>/edit', methods=['GET', 'POST'])
@login_required
def address_edit(addr_id):
    addr = DeliveryAddress.query.filter_by(id=addr_id, user_id=current_user.id).first_or_404()
    if request.method == 'POST':
        err = _save_address(addr)
        if err:
            flash(err, 'error')
            return redirect(url_for('user.address_edit', addr_id=addr_id))
        flash('Address updated!', 'success')
        return redirect(url_for('user.addresses'))
    return render_template('user/address_form.html', address=addr, labels=ADDRESS_LABELS)


@user_bp.route('/addresses/<int:addr_id>/delete', methods=['POST'])
@login_required
def address_delete(addr_id):
    addr = DeliveryAddress.query.filter_by(id=addr_id, user_id=current_user.id).first_or_404()
    was_default = addr.is_default
    db.session.delete(addr)
    db.session.commit()
    # If deleted address was default, promote the first remaining one
    if was_default:
        first = DeliveryAddress.query.filter_by(user_id=current_user.id).first()
        if first:
            first.is_default = True
            db.session.commit()
    flash('Address deleted.', 'success')
    return redirect(url_for('user.addresses'))


@user_bp.route('/addresses/<int:addr_id>/set-default', methods=['POST'])
@login_required
def address_set_default(addr_id):
    # Unset all defaults for this user
    DeliveryAddress.query.filter_by(user_id=current_user.id)\
                         .update({'is_default': False})
    addr = DeliveryAddress.query.filter_by(id=addr_id, user_id=current_user.id).first_or_404()
    addr.is_default = True
    db.session.commit()
    flash('Default address updated!', 'success')
    return redirect(url_for('user.addresses'))


def _save_address(existing):
    """Validate and save (create or update) a delivery address from form data.
    Returns an error string or None on success."""
    f = request.form
    recipient_name = f.get('recipient_name', '').strip()
    phone = _normalise_phone(f.get('phone', ''))
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

    # Validation
    if not recipient_name:
        return 'Recipient name is required.'
    if not division or not district or not upazila:
        return 'Please select Division, District and Upazila.'
    if label not in ADDRESS_LABELS:
        label = 'Home'

    if is_default:
        DeliveryAddress.query.filter_by(user_id=current_user.id)\
                             .update({'is_default': False})

    # If this is the user's first address, make it default automatically
    if not existing:
        count = DeliveryAddress.query.filter_by(user_id=current_user.id).count()
        if count == 0:
            is_default = True
        addr = DeliveryAddress(user_id=current_user.id)
        db.session.add(addr)
    else:
        addr = existing

    addr.recipient_name = recipient_name
    addr.phone = phone
    addr.division = division
    addr.district = district
    addr.upazila = upazila
    addr.union_ward = union_ward or None
    addr.area = area or None
    addr.road = road or None
    addr.house_no = house_no or None
    addr.apartment = apartment or None
    addr.postal_code = postal_code or None
    addr.delivery_instructions = delivery_instructions or None
    addr.maps_link = maps_link or None
    addr.label = label
    addr.is_default = is_default

    db.session.commit()
    return None


# -------------------------------------------------------
# Orders
# -------------------------------------------------------

@user_bp.route('/orders')
@login_required
def orders():
    page = request.args.get('page', 1, type=int)
    pagination = Order.query.filter_by(user_id=current_user.id)\
                            .order_by(Order.created_at.desc())\
                            .paginate(page=page, per_page=10)
    return render_template('user/orders.html', pagination=pagination)


@user_bp.route('/orders/<int:order_id>')
@login_required
def order_detail(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    return render_template('user/order_detail.html', order=order)


# -------------------------------------------------------
# Change Password
# -------------------------------------------------------

@user_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    # Social-only accounts have no password
    if current_user.social_provider and not current_user.password_hash:
        flash('Your account uses Google login. You cannot set a password here.', 'info')
        return redirect(url_for('user.profile'))

    if request.method == 'POST':
        current_pw = request.form.get('current_password', '')
        new_pw = request.form.get('new_password', '')
        confirm_pw = request.form.get('confirm_password', '')

        if not current_user.check_password(current_pw):
            flash('Current password is incorrect.', 'error')
            return redirect(url_for('user.change_password'))
        if len(new_pw) < 6:
            flash('New password must be at least 6 characters.', 'error')
            return redirect(url_for('user.change_password'))
        if new_pw != confirm_pw:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('user.change_password'))

        current_user.set_password(new_pw)
        db.session.commit()
        flash('Password changed successfully!', 'success')
        return redirect(url_for('user.profile'))

    return render_template('user/change_password.html')
