

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, inspect
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os
from datetime import datetime, date, timedelta
import pytz
from urllib.parse import quote_plus
import random
from functools import wraps
import time
import cloudinary
import cloudinary.uploader
# Added Flask-Mail import
from flask_mail import Mail, Message as FlaskMessage

# --- Local Module Imports ---
from ml_model.predictor import predict_disease, get_crop_advice
from scripts.price_scraper import get_market_prices

# --- Initial Setup ---
load_dotenv()
app = Flask(__name__)
app.secret_key = 'your_super_secret_key'

# --- Cloudinary Configuration ---
cloudinary.config(
    cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key = os.getenv('CLOUDINARY_API_KEY'),
    api_secret = os.getenv('CLOUDINARY_API_SECRET')
)

# --- Flask-Mail SMTP Configuration ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'your-email@gmail.com')
# Use a secure Google App Password in your .env file, not your real password
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', 'your-app-password') 
mail = Mail(app)

# --- Database Configuration ---
db_url = os.getenv('DATABASE_URL')
if not db_url:
    project_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(project_dir, "instance", "krishimitra.sqlite")
    os.makedirs(os.path.join(project_dir, "instance"), exist_ok=True)
    db_url = f"sqlite:///{db_path}"
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Configuration ---
app.config['LEAF_UPLOAD_FOLDER'] = 'static/leaf_uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# --- DATABASE MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mobile = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    products = db.relationship('Product', backref='seller_user', lazy=True)
    services = db.relationship('Service', backref='provider', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(255), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_type = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price_details = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    messages = db.relationship('Message', backref='conversation', lazy=True, cascade="all, delete-orphan")
    product = db.relationship('Product', backref='conversations')
    service = db.relationship('Service', backref='conversations')
    buyer = db.relationship('User', foreign_keys=[buyer_id])
    seller = db.relationship('User', foreign_keys=[seller_id])

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    sender = db.relationship('User', foreign_keys=[sender_id])

# --- Database Context Check ---
with app.app_context():
    inspector = inspect(db.engine)
    if not inspector.has_table("user"):
        print("Database tables not found, creating them...")
        db.create_all()
        print("Database tables created.")
    else:
        print("Database tables already exist.")

# --- Helper Functions and Decorators ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

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

# --- ROUTES ---
@app.route('/')
def home():
    return render_template('index.html')

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

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            otp = str(random.randint(100000, 999999))
            session['reset_otp'] = otp
            session['reset_user'] = user.email
            
            
            try:
                
                msg = FlaskMessage(
                    subject="Krishimitra - Password Reset OTP",
                    sender=app.config['MAIL_USERNAME'],
                    recipients=[user.email]
                )
                msg.body = f"Hello,\n\nYour OTP for resetting your Krishimitra password is: {otp}.\n\nPlease do not share this OTP with anyone."
                
                mail.send(msg)
                
                flash('An OTP has been sent securely to your registered email address.', 'success')
                return redirect(url_for('verify_otp'))
            except Exception as e:
                print(f"SMTP Error: {e}")
                flash('Failed to dispatch OTP email. Check server setup or credentials.', 'error')
                return redirect(url_for('forgot_password'))
        else:
            flash('This email address is not registered.', 'error')
    return render_template('forgot_password.html')

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
        file_to_upload = request.files.get('image')
        if file_to_upload:
            upload_result = cloudinary.uploader.upload(file_to_upload)
            image_url = upload_result['secure_url']
            new_product = Product(name=request.form['name'], category=request.form['category'], description=request.form['description'], price=request.form['price'], image=image_url, seller_id=session.get('user_id'))
            db.session.add(new_product)
            db.session.commit()
            flash('Your product has been listed successfully!', 'success')
            return redirect(url_for('dashboard'))
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
        file_to_upload = request.files.get('image')
        if file_to_upload and file_to_upload.filename != '':
            upload_result = cloudinary.uploader.upload(file_to_upload)
            product.image = upload_result['secure_url']
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

@app.route('/edit_service/<int:service_id>', methods=['GET', 'POST'])
@login_required
def edit_service(service_id):
    service = Service.query.get_or_404(service_id)
    if service.provider_id != session.get('user_id'):
        flash('You are not authorized to edit this service.', 'error')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        service.service_type = request.form['service_type']
        service.description = request.form['description']
        service.price_details = request.form['price_details']
        service.location = request.form['location']
        db.session.commit()
        flash('Your service has been updated successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('edit_service.html', service=service)

@app.route('/delete_service/<int:service_id>', methods=['POST'])
@login_required
def delete_service(service_id):
    service = Service.query.get_or_404(service_id)
    if service.provider_id != session.get('user_id'):
        flash('You are not authorized to delete this service.', 'error')
        return redirect(url_for('find_services'))
    db.session.delete(service)
    db.session.commit()
    flash('Service has been deleted successfully.', 'success')
    return redirect(url_for('find_services'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_products = Product.query.filter_by(seller_id=session['user_id']).order_by(Product.id.desc()).all()
    user_services = Service.query.filter_by(provider_id=session['user_id']).order_by(Service.id.desc()).all()
    return render_template('dashboard.html', products=user_products, services=user_services)

@app.route('/detect', methods=['GET', 'POST'])
def disease_detection():
    if request.method == 'POST':
        if 'leaf_image' not in request.files or request.files['leaf_image'].filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
        file = request.files['leaf_image']
        if file and allowed_file(file.filename):
            leaf_upload_folder = app.config['LEAF_UPLOAD_FOLDER']
            os.makedirs(leaf_upload_folder, exist_ok=True)
            filename = secure_filename(file.filename)
            leaf_upload_path = os.path.join(leaf_upload_folder, filename)
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
    markets = ["Pune", "Nashik", "Mumbai", "Nagpur", "Satara", "Kolhapur", "Ahmednagar", "Akola", "Aurangabad", "Baramati", "Dhule", "Jalgaon", "Latur", "Nanded", "Osmanabad", "Rahuri", "Sangamner"]
    commodities = ["Tomato", "Onion", "Potato", "Brinjal", "Cabbage", "Cauliflower", "Lady's Finger", "Bitter Gourd", "Bottle Gourd", "Cucumber", "Green Chilli", "Garlic", "Ginger(Green)", "Lemon"]
    selected_market = request.args.get('market')
    selected_commodity = request.args.get('commodity')
    date_choice = request.args.get('date', 'today')
    if date_choice == 'yesterday':
        target_date = date.today() - timedelta(days=1)
    else:
        target_date = date.today()
    date_str = target_date.strftime('%Y-%m-%d')
    price_data = get_market_prices(market=selected_market, commodity=selected_commodity, date_str=date_str)
    market_status_message, market_is_open = get_market_status()
    return render_template('market_prices.html', prices=price_data, markets=markets, commodities=commodities, selected_market=selected_market, selected_commodity=selected_commodity, date_choice=date_choice, market_status_message=market_status_message, market_is_open=market_is_open)

@app.route('/conversation/start/product/<int:product_id>')
@login_required
def conversation_start_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.seller_id == session['user_id']:
        flash('You cannot start a conversation with yourself.', 'error')
        return redirect(url_for('store'))
    convo = Conversation.query.filter_by(product_id=product.id, buyer_id=session['user_id']).first()
    if not convo:
        convo = Conversation(product_id=product.id, buyer_id=session['user_id'], seller_id=product.seller_id)
        db.session.add(convo)
        db.session.commit()
    return redirect(url_for('conversation_chat', convo_id=convo.id))

@app.route('/conversation/start/service/<int:service_id>')
@login_required
def conversation_start_service(service_id):
    service = Service.query.get_or_404(service_id)
    if service.provider_id == session['user_id']:
        flash('You cannot start a conversation with yourself.', 'error')
        return redirect(url_for('find_services'))
    convo = Conversation.query.filter_by(service_id=service.id, buyer_id=session['user_id']).first()
    if not convo:
        convo = Conversation(service_id=service.id, buyer_id=session['user_id'], seller_id=service.provider_id)
        db.session.add(convo)
        db.session.commit()
    return redirect(url_for('conversation_chat', convo_id=convo.id))

@app.route('/conversation/chat/<int:convo_id>', methods=['GET', 'POST'])
@login_required
def conversation_chat(convo_id):
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
        return redirect(url_for('conversation_chat', convo_id=convo.id))
    return render_template('conversation.html', conversation=convo)

@app.route('/inbox')
@login_required
def inbox():
    conversations = Conversation.query.filter(or_(Conversation.buyer_id == session['user_id'], Conversation.seller_id == session['user_id'])).all()
    conversations.sort(key=lambda c: c.messages[-1].timestamp if c.messages else datetime.min, reverse=True)
    return render_template('inbox.html', conversations=conversations)

@app.route('/about')
def about():
    return render_template('about.html')
    
@app.route('/admin')
@admin_required
def admin_dashboard():
    all_users = User.query.order_by(User.id).all()
    all_products = Product.query.order_by(Product.id.desc()).all()
    user_count = User.query.count()
    product_count = Product.query.count()
    conversation_count = Conversation.query.count()
    return render_template('admin_dashboard.html', users=all_users, products=all_products, user_count=user_count, product_count=product_count, conversation_count=conversation_count)
    
@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    if user_id == session.get('user_id'):
        flash('You cannot delete your own admin account.', 'error')
        return redirect(url_for('admin_dashboard'))
    user_to_delete = User.query.get_or_404(user_id)
    Product.query.filter_by(seller_id=user_id).delete()
    Service.query.filter_by(provider_id=user_id).delete()
    db.session.delete(user_to_delete)
    db.session.commit()
    flash(f"User {user_to_delete.email} has been deleted successfully.", 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_product/<int:product_id>', methods=['POST'])
@admin_required
def admin_delete_product(product_id):
    product_to_delete = Product.query.get_or_404(product_id)
    db.session.delete(product_to_delete)
    db.session.commit()
    flash(f"Product '{product_to_delete.name}' has been deleted by an admin.", 'success')
    return redirect(request.referrer or url_for('store'))

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if 'reset_otp' not in session or 'reset_user' not in session:
        return redirect(url_for('forgot_password'))
    if request.method == 'POST':
        user_otp = request.form.get('otp')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        if user_otp != session.get('reset_otp'):
            flash('Invalid OTP.', 'error')
            return redirect(url_for('verify_otp'))
        if new_password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('verify_otp'))
        user_to_update = User.query.filter_by(email=session['reset_user']).first()
        if user_to_update:
            user_to_update.password = generate_password_hash(new_password)
            db.session.commit()
            session.pop('reset_otp', None)
            session.pop('reset_user', None)
            flash('Your password has been reset successfully! Please log in.', 'success')
            return redirect(url_for('login'))
    return render_template('verify_otp.html')

@app.route('/crop_advisory', methods=['GET', 'POST'])
@login_required
def crop_advisory():
    if request.method == 'POST':
        user_question = request.form.get('user_question')
        if user_question:
            ai_answer = get_crop_advice(user_question)
            return render_template('crop_advisory.html', user_question=user_question, ai_answer=ai_answer)
    return render_template('crop_advisory.html', user_question=None, ai_answer=None)

@app.route('/contact')
def contact_admin():
    return render_template('contact_admin.html')

@app.route('/services')
def find_services():
    search_location = request.args.get('location', '').lower()
    query = Service.query
    if search_location:
        query = query.filter(Service.location.ilike(f'%{search_location}%'))
    services = query.order_by(Service.id.desc()).all()
    return render_template('find_services.html', services=services, search_location=request.args.get('location', ''))

@app.route('/offer_service', methods=['GET', 'POST'])
@login_required
def offer_service():
    if request.method == 'POST':
        new_service = Service(
            service_type=request.form['service_type'],
            description=request.form['description'],
            price_details=request.form['price_details'],
            location=request.form['location'],
            provider_id=session['user_id']
        )
        db.session.add(new_service)
        db.session.commit()
        flash('Your service has been listed successfully!', 'success')
        return redirect(url_for('find_services'))
    return render_template('offer_service.html')

if __name__ == '__main__':
    app.run(debug=True)
