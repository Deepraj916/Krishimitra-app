# app.py - FINAL DATABASE VERSION (with Auto-Create)

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, inspect
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
from ml_model.predictor import predict_disease, get_crop_advice
from scripts.price_scraper import get_market_prices

# --- Initial Setup ---
load_dotenv()
app = Flask(__name__)
app.secret_key = 'your_super_secret_key'

# --- Database Configuration ---
# This new logic checks if the live DATABASE_URL from Render exists.
# If not, it creates and uses a local database file named 'instance/krishimitra.sqlite'.
db_url = os.getenv('DATABASE_URL')
if not db_url:
    # Set up the path for the local SQLite database
    project_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(project_dir, "instance", "krishimitra.sqlite")
    # Ensure the 'instance' directory exists so the file can be created
    os.makedirs(os.path.join(project_dir, "instance"), exist_ok=True)
    db_url = f"sqlite:///{db_path}"
else:
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Configuration ---
UPLOAD_FOLDER = 'static/product_uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# --- DATABASE MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True)
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

# --- This block runs ONCE when the app starts up ---
with app.app_context():
    inspector = inspect(db.engine)
    if not inspector.has_table("user"):
        print("Database tables not found, creating them...")
        db.create_all()
        print("Database tables created.")
    else:
        print("Database tables already exist.")

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

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # First check if the user is logged in at all
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        # Then check if the user's role is 'admin'
        if session.get('role') != 'admin':
            flash('You do not have the required permissions to access this page.', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def get_market_status():
    IST = pytz.timezone('Asia/Kolkata')
    now = datetime.now(IST)
    if now.weekday() == 6: return "Today is a holiday, the market is closed.", False
    if 10 <= now.hour < 18: return f"Market is currently open. (Current time: {now.strftime('%I:%M %p')})", True
    else: return f"Market is currently closed (10 AM - 6 PM IST). (Current time: {now.strftime('%I:%M %p')})", False

from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- ROUTES ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname, email, mobile, password = request.form['fullname'], request.form['email'], request.form['mobile'], request.form['password']
        if User.query.filter(or_(User.email == email, User.mobile == mobile)).first():
            flash('An account with this email or mobile number already exists.', 'error')
            return redirect(url_for('register'))
        new_user = User(name=fullname, email=email, mobile=mobile, password=generate_password_hash(password), role=request.form['role'])
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
            return redirect(url_for('login'))
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

@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
@seller_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.seller_id != session.get('user_id'):
        flash('You are not authorized to edit this product.', 'error')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        product.name, product.category, product.description, product.price = request.form['name'], request.form['category'], request.form['description'], request.form['price']
        file = request.files.get('image')
        if file and file.filename != '':
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                product.image = filename
        db.session.commit()
        flash('Your product has been updated successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('edit_product.html', product=product)
    
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

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    user_products = Product.query.filter_by(seller_id=session['user_id']).order_by(Product.id.desc()).all()
    return render_template('dashboard.html', products=user_products)

@app.route('/detect', methods=['GET', 'POST'])
def disease_detection():
    if request.method == 'POST':
        if 'leaf_image' not in request.files or request.files['leaf_image'].filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
        file = request.files['leaf_image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            leaf_upload_path = os.path.join('static/leaf_uploads', filename)
            file.save(leaf_upload_path)
            prediction_data = predict_disease(leaf_upload_path)
            keyword = prediction_data.get('product_keyword')
            suggested_products, amazon_link, flipkart_link = [], None, None
            if keyword:
                suggested_products = Product.query.filter(or_(Product.name.ilike(f'%{keyword}%'), Product.description.ilike(f'%{keyword}%'))).all()
                url_safe_keyword = quote_plus(keyword)
                amazon_link = f"https://www.amazon.in/s?k={url_safe_keyword}"
                flipkart_link = f"https://www.flipkart.com/search?q={url_safe_keyword}"
            return render_template('disease_detection.html', prediction_data=prediction_data, uploaded_image=filename, products=suggested_products, amazon_link=amazon_link, flipkart_link=flipkart_link)
    return render_template('disease_detection.html', prediction_data=None)

@app.route('/prices')
def market_prices():
    market_status_message, market_is_open = get_market_status()
    price_data = []
    if market_is_open:
        price_data = get_market_prices()
    return render_template('market_prices.html', prices=price_data, market_status_message=market_status_message, market_is_open=market_is_open)

@app.route('/conversation/start/<int:product_id>')
def conversation_start(product_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    product = Product.query.get_or_404(product_id)
    if product.seller_id == session['user_id']:
        flash('You cannot start a conversation with yourself.', 'error')
        return redirect(url_for('store'))
    convo = Conversation.query.filter_by(product_id=product.id, buyer_id=session['user_id'], seller_id=product.seller_id).first()
    if not convo:
        convo = Conversation(product_id=product.id, buyer_id=session['user_id'], seller_id=product.seller_id)
        db.session.add(convo)
        db.session.commit()
    return redirect(url_for('conversation_chat', convo_id=convo.id))

@app.route('/conversation/chat/<int:convo_id>', methods=['GET', 'POST'])
def conversation_chat(convo_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    convo = Conversation.query.get_or_404(convo_id)
    if session['user_id'] not in [convo.buyer_id, convo.seller_id]:
        flash('You do not have permission to view this conversation.', 'error')
        return redirect(url_for('inbox'))
    if request.method == 'POST':
        text = request.form.get('message_text')
        if text:
            msg = Message(conversation_id=convo.id, sender_id=session['user_id'], text=text, timestamp=datetime.utcnow())
            db.session.add(msg)
            db.session.commit()
        return redirect(url_for('conversation_chat', convo_id=convo_id))
    return render_template('conversation.html', conversation=convo)

@app.route('/inbox')
def inbox():
    if 'user_id' not in session: return redirect(url_for('login'))
    conversations = Conversation.query.filter(or_(Conversation.buyer_id == session['user_id'], Conversation.seller_id == session['user_id'])).order_by(Conversation.id.desc()).all()
    return render_template('inbox.html', conversations=conversations)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    # Placeholder
    return render_template('forgot_password.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    # Placeholder
    return render_template('verify_otp.html')

@app.route('/admin')
@admin_required
def admin_dashboard():
    # Fetch all users and all products from the database
    all_users = User.query.order_by(User.id).all()
    all_products = Product.query.order_by(Product.id.desc()).all()
    
    # --- START: New Statistics Logic ---
    # Calculate the total counts for key metrics
    user_count = User.query.count()
    product_count = Product.query.count()
    conversation_count = Conversation.query.count()
    # --- END: New Statistics Logic ---
    
    return render_template(
        'admin_dashboard.html', 
        users=all_users, 
        products=all_products,
        # Pass the new statistics to the page
        user_count=user_count,
        product_count=product_count,
        conversation_count=conversation_count
    )

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    # Prevent an admin from deleting their own account
    if user_id == session.get('user_id'):
        flash('You cannot delete your own admin account.', 'error')
        return redirect(url_for('admin_dashboard'))

    user_to_delete = User.query.get_or_404(user_id)

    # Optional: Before deleting the user, delete their products to keep the database clean
    Product.query.filter_by(seller_id=user_id).delete()

    db.session.delete(user_to_delete)
    db.session.commit()

    flash(f"User {user_to_delete.email} has been deleted successfully.", 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_product/<int:product_id>', methods=['POST'])
@admin_required
def admin_delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product has been deleted successfully.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/crop_advisory', methods=['GET', 'POST'])
@login_required
def crop_advisory():
    if request.method == 'POST':
        user_question = request.form.get('user_question')
        if user_question:
            # Get the expert answer from our new function
            ai_answer = get_crop_advice(user_question)
            return render_template('crop_advisory.html', user_question=user_question, ai_answer=ai_answer)

    # This is for when the user first visits the page
    return render_template('crop_advisory.html', user_question=None, ai_answer=None)

if __name__ == '__main__':
    app.run(debug=True)
