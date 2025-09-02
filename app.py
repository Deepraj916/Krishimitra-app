# app.py - FINAL DATABASE VERSION

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os
from datetime import datetime
import pytz
from urllib.parse import quote_plus
import random
from functools import wraps

# --- Local Module Imports ---
# Make sure these files exist and are correct
# from ml_model.predictor import predict_disease
# from scripts.price_scraper import get_market_prices

# --- Initial Setup ---
load_dotenv()
app = Flask(__name__)
app.secret_key = 'your_super_secret_key'

# --- Database Configuration ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Configuration ---
UPLOAD_FOLDER = 'static/product_uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# --- DATABASE MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mobile = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    products = db.relationship('Product', backref='seller_user', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(100), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    messages = db.relationship('Message', backref='conversation', lazy=True, cascade="all, delete-orphan")
    product = db.relationship('Product', backref='conversations')
    buyer = db.relationship('User', foreign_keys=[buyer_id])
    seller = db.relationship('User', foreign_keys=[seller_id])

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    sender = db.relationship('User', foreign_keys=[sender_id])

# --- Helper Functions ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def seller_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'seller':
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('store'))
        return f(*args, **kwargs)
    return decorated_function

def get_market_status():
    IST = pytz.timezone('Asia/Kolkata')
    now = datetime.now(IST)
    if now.weekday() == 6: return "Today is a holiday, the market is closed.", False
    if 10 <= now.hour < 18: return f"Market is currently open. (Current time: {now.strftime('%I:%M %p')})", True
    else: return f"Market is currently closed (10 AM - 6 PM IST). (Current time: {now.strftime('%I:%M %p')})", False

# --- ROUTES ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email, mobile, password = request.form['email'], request.form['mobile'], request.form['password']
        if User.query.filter(or_(User.email == email, User.mobile == mobile)).first():
            flash('An account with this email or mobile number already exists.', 'error')
            return redirect(url_for('register'))
        new_user = User(email=email, mobile=mobile, password=generate_password_hash(password), role=request.form['role'])
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier, password = request.form['email'], request.form['password']
        user = User.query.filter(or_(User.email == identifier, User.mobile == identifier)).first()
        if user and check_password_hash(user.password, password):
            session['user_id'], session['user_email'], session['role'] = user.id, user.email, user.role
            flash('Logged in successfully!', 'success')
            return redirect(url_for('store'))
        else:
            flash('Invalid credentials. Please try again.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))

@app.route('/store')
def store():
    query = Product.query
    search_term, category = request.args.get('search', '').lower(), request.args.get('category')
    if category: query = query.filter(Product.category == category)
    if search_term: query = query.filter(or_(Product.name.ilike(f'%{search_term}%'), Product.description.ilike(f'%{search_term}%')))
    products = query.order_by(Product.id.desc()).all()
    amazon_link, flipkart_link = None, None
    if not products and search_term:
        url_safe_keyword = quote_plus(search_term)
        amazon_link = f"https://www.amazon.in/s?k={url_safe_keyword}"
        flipkart_link = f"https://www.flipkart.com/search?q={url_safe_keyword}"
    return render_template('store.html', products=products, active_category=category, search_query=search_term, amazon_link=amazon_link, flipkart_link=flipkart_link)

@app.route('/add_product', methods=['GET', 'POST'])
@seller_required
def add_product():
    if request.method == 'POST':
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            new_product = Product(name=request.form['name'], category=request.form['category'], description=request.form['description'], price=request.form['price'], image=filename, seller_id=session['user_id'])
            db.session.add(new_product)
            db.session.commit()
            flash('Your product has been listed!', 'success')
            return redirect(url_for('store'))
    return render_template('add_product.html')

@app.route('/delete_product/<int:product_id>', methods=['POST'])
@seller_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.seller_id != session.get('user_id'):
        flash('You are not authorized to delete this product.', 'error')
        return redirect(url_for('store'))
    db.session.delete(product)
    db.session.commit()
    flash('Product has been deleted successfully.', 'success')
    return redirect(url_for('store'))

# --- Add all other routes for disease detection, prices, messaging, and password reset here ---
# These routes will need to be similarly converted to use the database models.
# For example, disease_detection would query the Product model for suggested products.
# The conversation routes would query the Conversation and Message models.

# This special route is for creating the database tables for the first time.
@app.route('/init-db')
def init_db():
    with app.app_context():
        db.create_all()
    return "Database tables created!"

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # For local development, create tables if they don't exist.
    app.run(debug=True)

