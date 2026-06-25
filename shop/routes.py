from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response
from flask_login import login_required, current_user
from extensions import db
from models import Category, Product

shop_bp = Blueprint('shop', __name__)

@shop_bp.route('/')
def index():
    categories = Category.query.all()
    featured = Product.query.filter_by(is_featured=True).all()
    return render_template('index.html', categories=categories, featured=featured)

@shop_bp.route('/category/<cat_id>')
def category(cat_id):
    cat = Category.query.get_or_404(cat_id)
    products = Product.query.filter_by(category_id=cat_id).all()
    return render_template('category.html', category=cat, products=products)

@shop_bp.route('/contact')
def contact():
    return render_template('contact.html')
