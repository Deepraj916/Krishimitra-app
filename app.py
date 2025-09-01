from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime
from urllib.parse import quote_plus
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from functools import wraps
import json
import random
from email_utils import send_otp_email

# --- Local Module Imports ---
from ml_model.predictor import predict_disease
from scripts.price_scraper import get_market_prices
import os

# --- Initial Setup ---
load_dotenv()
app = Flask(__name__)
app.secret_key = 'your_super_secret_key'

# --- Configuration ---
UPLOAD_FOLDER = 'static/product_uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# --- File Paths ---
USERS_DATA_FILE = os.path.join('data', 'users.json')
PRODUCTS_DATA_FILE = os.path.join('data', 'products.json')
REMEDIES_DATA_FILE = os.path.join('data', 'remedies.json')
MESSAGES_DATA_FILE = os.path.join('data', 'messages.json')

# --- Helper Functions ---
def load_data(file_path):
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return []
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def save_data(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

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

# --- ROUTES ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        users = load_data(USERS_DATA_FILE)
        if any(user['email'] == email for user in users):
            flash('An account with this email already exists.', 'error')
            return redirect(url_for('register'))
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(password)
        new_user = {'id': len(users) + 1, 'email': email, 'password': hashed_password, 'role': request.form['role']}
        users.append(new_user)
        save_data(users, USERS_DATA_FILE)
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        users = load_data(USERS_DATA_FILE)
        user = next((user for user in users if user['email'] == email), None)
        if user and check_password_hash(user['password'], password):
            session['user_email'] = user['email']
            session['role'] = user.get('role', 'customer')
            flash('Logged in successfully!', 'success')
            return redirect(url_for('store'))
        else:
            flash('Invalid credentials. Please try again.', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_email', None)
    session.pop('role', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))

@app.route('/store')
def store():
    search_query = request.args.get('search', '').lower()
    category_filter = request.args.get('category', None)
    all_products = load_data(PRODUCTS_DATA_FILE)

    # Filter by category first
    if category_filter:
        products_in_category = [p for p in all_products if p.get('category') == category_filter]
    else:
        products_in_category = all_products

    # Then, filter by search query
    if search_query:
        final_products = [p for p in products_in_category if search_query in p['name'].lower() or search_query in p['description'].lower()]
    else:
        final_products = products_in_category

    # --- NEW LOGIC ---
    # If the search returned no results, generate external links
    amazon_link = None
    flipkart_link = None
    if not final_products and search_query:
        url_safe_keyword = quote_plus(search_query)
        amazon_link = f"https://www.amazon.in/s?k={url_safe_keyword}"
        flipkart_link = f"https://www.flipkart.com/search?q={url_safe_keyword}"
    # -----------------

    return render_template(
        'store.html', 
        products=final_products, 
        search_query=request.args.get('search', ''),
        active_category=category_filter,
        amazon_link=amazon_link,      # Pass the new links
        flipkart_link=flipkart_link   # Pass the new links
    )

@app.route('/add_product', methods=['GET', 'POST'])
@seller_required
def add_product():
    if request.method == 'POST':
        # --- THIS IS THE CORRECTED LOGIC ---
        # 1. First, check if the image key exists in the request
        if 'image' not in request.files:
            flash('No image file part', 'error')
            return redirect(request.url)

        # 2. Now, it's safe to get the file object
        file = request.files['image']

        # 3. Then, check if the user actually selected a file
        if file.filename == '':
            flash('No selected image file', 'error')
            return redirect(request.url)
        # ------------------------------------
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            products = load_data(PRODUCTS_DATA_FILE)
            new_product = {
                'id': len(products) + 1,
                'name': request.form['name'],
                'category': request.form['category'],
                'description': request.form['description'],
                'price': request.form['price'],
                'image': filename,
                'seller': session['user_email']
            }
            products.append(new_product)
            save_data(products, PRODUCTS_DATA_FILE)
            flash('Your product has been listed!', 'success')
            return redirect(url_for('store'))

    return render_template('add_product.html')

@app.route('/delete_product/<int:product_id>', methods=['POST'])
@seller_required
def delete_product(product_id):
    if 'user_email' not in session:
        flash('You must be logged in to perform this action.', 'error')
        return redirect(url_for('login'))
    products = load_data(PRODUCTS_DATA_FILE)
    product_to_delete = next((p for p in products if p['id'] == product_id), None)
    if not product_to_delete:
        flash('Product not found.', 'error')
        return redirect(url_for('store'))
    if product_to_delete['seller'] != session['user_email']:
        flash('You are not authorized to delete this product.', 'error')
        return redirect(url_for('store'))
    try:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], product_to_delete['image'])
        if os.path.exists(image_path):
            os.remove(image_path)
    except Exception as e:
        print(f"Error deleting image file: {e}")
    updated_products = [p for p in products if p['id'] != product_id]
    save_data(updated_products, PRODUCTS_DATA_FILE)
    flash('Product has been deleted successfully.', 'success')
    return redirect(url_for('store'))

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
            
            suggested_products = []
            amazon_link = None
            flipkart_link = None
            
            if keyword:
                all_products = load_data(PRODUCTS_DATA_FILE)
                suggested_products = [p for p in all_products if keyword.lower() in p['name'].lower() or keyword.lower() in p['description'].lower()]
                url_safe_keyword = quote_plus(keyword)
                amazon_link = f"https://www.amazon.in/s?k={url_safe_keyword}"
                flipkart_link = f"https://www.flipkart.com/search?q={url_safe_keyword}"

            return render_template(
                'disease_detection.html', 
                prediction_data=prediction_data,  # Pass the entire dictionary
                uploaded_image=filename, 
                products=suggested_products,
                amazon_link=amazon_link,
                flipkart_link=flipkart_link
            )

    return render_template('disease_detection.html', prediction_data=None)
@app.route('/prices')
def market_prices():
    price_data = get_market_prices()
    return render_template('market_prices.html', prices=price_data)

@app.route('/inbox')
def inbox():
    if 'user_email' not in session:
        flash('You must be logged in to view your inbox.', 'error')
        return redirect(url_for('login'))

    all_conversations = load_data(MESSAGES_DATA_FILE)
    all_products = load_data(PRODUCTS_DATA_FILE)
    
    user_conversations = [c for c in all_conversations if session['user_email'] in c.get('participants', [])]
    
    for convo in user_conversations:
        product = next((p for p in all_products if p.get('id') == convo.get('product_id')), None)
        convo['product_name'] = product['name'] if product else "Unknown Product"
        other_participant = next((p for p in convo['participants'] if p != session['user_email']), None)
        convo['other_participant'] = other_participant
    
    # Sort conversations to show the most recent ones first
    user_conversations.sort(key=lambda c: c['messages'][-1]['timestamp'] if c['messages'] else '0', reverse=True)

    return render_template('inbox.html', conversations=user_conversations)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        users = load_data(USERS_DATA_FILE)
        user = next((u for u in users if u['email'] == email), None)

        if user:
            otp = str(random.randint(100000, 999999))
            session['reset_otp'] = otp
            session['reset_user'] = user['email']

            email_sent = send_otp_email(user['email'], otp)

            if email_sent:
                flash(f"An OTP has been sent to {user['email']}", 'info')
                return redirect(url_for('verify_otp'))
            else:
                flash('Could not send OTP email. Please try again later.', 'error')
        else:
            flash('This email address is not registered.', 'error')
    return render_template('forgot_password.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if 'reset_otp' not in session or 'reset_user' not in session:
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        user_otp = request.form.get('otp')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if user_otp != session.get('reset_otp'):
            flash('Invalid OTP. Please try again.', 'error')
            return redirect(url_for('verify_otp'))
            
        if new_password != confirm_password:
            flash('New passwords do not match.', 'error')
            return redirect(url_for('verify_otp'))

        # If OTP is correct, proceed to update the password
        users = load_data(USERS_DATA_FILE)
        user_to_update = next((u for u in users if u['email'] == session['reset_user']), None)
        
        if user_to_update:
            # Securely hash the new password before saving
            user_to_update['password'] = generate_password_hash(new_password)
            save_data(users, USERS_DATA_FILE)
            
            # Clean up the session
            session.pop('reset_otp', None)
            session.pop('reset_user', None)
            
            flash('Your password has been reset successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('An unexpected error occurred. User not found.', 'error')
            return redirect(url_for('forgot_password'))

    return render_template('verify_otp.html')

if __name__ == '__main__':
    app.run(debug=True)
