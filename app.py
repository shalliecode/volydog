from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import json
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'user_login'
login_manager.login_message_category = 'info'

# Create upload folder
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/images', exist_ok=True)

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    orders = db.relationship('Order', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    breed = db.Column(db.String(100))
    gender = db.Column(db.String(10))
    age = db.Column(db.String(20))
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    image_urls = db.Column(db.JSON)  # store list of image paths
    additional_details = db.Column(db.JSON)  # For dynamic product details
    rating = db.Column(db.Float, default=0.0)
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    orders = db.relationship('OrderItem', backref='product', lazy=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(120), nullable=False)
    customer_phone = db.Column(db.String(20))
    customer_address = db.Column(db.Text)
    payment_method = db.Column(db.String(20))  # bank, paypal, crypto
    payment_status = db.Column(db.String(20), default='pending')  # pending, paid, refunded
    status = db.Column(db.String(20), default='pending')  # pending, processing, completed, cancelled
    total_amount = db.Column(db.Float, nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)


class SiteSettings(db.Model):
    """Simple site-wide settings editable by an admin user."""
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    whatsapp = db.Column(db.String(50))
    contact_email = db.Column(db.String(120))
    business_hours = db.Column(db.String(255))
    social_links = db.Column(db.JSON)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.context_processor
def inject_breeds():
    # Provide cleaned, unique list of breeds to all templates
    try:
        raw_breeds = [b[0] for b in db.session.query(Product.breed).filter(Product.breed.isnot(None)).all()]
        cleaned = []
        for r in raw_breeds:
            if not r:
                continue
            c = r.strip().title()
            if c and c not in cleaned:
                cleaned.append(c)
        return {'breeds': cleaned}
    except Exception:
        return {'breeds': []}


@app.context_processor
def inject_current_time():
    # Provide current time to templates (useful for headers/footers)
    try:
        return {'current_time': datetime.utcnow()}
    except Exception:
        return {'current_time': datetime.now()}


@app.context_processor
def inject_site_settings():
    """Expose site settings to all templates as `site_settings` (may be None)."""
    try:
        settings = SiteSettings.query.first()
        return {'site_settings': settings}
    except Exception:
        return {'site_settings': None}

# Utility functions
def generate_order_number():
    from datetime import datetime
    return f"VELY{datetime.now().strftime('%Y%m%d%H%M%S')}"

def send_order_email(order):
    # Placeholder for email sending functionality
    # You would implement this with your email service
    pass

def send_whatsapp_notification(order):
    # Placeholder for WhatsApp notification
    # You would implement this with Twilio or similar service
    pass

# Routes
@app.route('/')
def index():
    products = Product.query.filter_by(is_available=True).all()
    return render_template('index.html', products=products)

@app.route('/puppies')
def puppies():
    # Only show products that have a breed assigned by default
    breed = request.args.get('breed')
    if breed:
        # normalize incoming breed parameter to match stored format
        breed = breed.strip().title()
        products = Product.query.filter_by(breed=breed, is_available=True).all()
    else:
        products = Product.query.filter(Product.breed.isnot(None), Product.is_available==True).all()

    # build cleaned unique breed list
    raw_breeds = [b[0] for b in db.session.query(Product.breed).filter(Product.breed.isnot(None)).all()]
    cleaned = []
    for r in raw_breeds:
        if not r:
            continue
        c = r.strip().title()
        if c and c not in cleaned:
            cleaned.append(c)

    return render_template('product/products.html', 
                         products=products, 
                         breeds=cleaned)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product/product_detail.html', product=product)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        # Process order
        order_number = generate_order_number()
        
        order = Order(
            order_number=order_number,
            customer_name=request.form.get('name'),
            customer_email=request.form.get('email'),
            customer_phone=request.form.get('phone'),
            customer_address=request.form.get('address'),
            payment_method=request.form.get('payment_method'),
            total_amount=float(request.form.get('total_amount')),
            notes=request.form.get('notes')
        )
        
        if current_user.is_authenticated:
            order.user_id = current_user.id
        
        db.session.add(order)
        
        # Add order items (simplified - in reality you'd get from cart)
        product_id = request.form.get('product_id')
        if product_id:
            product = Product.query.get(product_id)
            order_item = OrderItem(
                order=order,
                product_id=product_id,
                quantity=1,
                price=product.price
            )
            db.session.add(order_item)
        
        db.session.commit()
        
        # Send notifications
        send_order_email(order)
        send_whatsapp_notification(order)
        
        flash('Order placed successfully! Admin will contact you for payment processing.', 'success')
        return redirect(url_for('index'))
    
    product_id = request.args.get('product_id')
    product = None
    if product_id:
        product = Product.query.get(product_id)
    
    return render_template('checkout.html', product=product)

@app.route('/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            
            # Check if admin
            if user.is_admin:
                return redirect(next_page or url_for('admin_dashboard'))
            
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('user/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('user_login'))
    
    return render_template('user/register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Process contact form
        flash('Message sent successfully!', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/reviews')
def reviews():
    return render_template('review.html')

# Admin Routes
@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    stats = {
        'total_orders': Order.query.count(),
        'pending_orders': Order.query.filter_by(status='pending').count(),
        'total_products': Product.query.count(),
        'total_users': User.query.count()
    }
    
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html', stats=stats, orders=recent_orders)


@app.route('/admin/site-settings', methods=['GET', 'POST'])
@login_required
def admin_site_settings():
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))

    settings = SiteSettings.query.first()

    if request.method == 'POST':
        location = request.form.get('location')
        phone = request.form.get('phone')
        whatsapp = request.form.get('whatsapp')
        contact_email = request.form.get('contact_email')
        business_hours = request.form.get('business_hours')
        # Social links
        social_facebook = request.form.get('social_facebook', '').strip()
        social_twitter = request.form.get('social_twitter', '').strip()
        social_instagram = request.form.get('social_instagram', '').strip()
        social_youtube = request.form.get('social_youtube', '').strip()

        social_links = {
            'facebook': social_facebook,
            'twitter': social_twitter,
            'instagram': social_instagram,
            'youtube': social_youtube
        }

        if not settings:
            settings = SiteSettings(
                location=location,
                phone=phone,
                whatsapp=whatsapp,
                contact_email=contact_email,
                business_hours=business_hours,
                social_links=social_links
            )
            db.session.add(settings)
        else:
            settings.location = location
            settings.phone = phone
            settings.whatsapp = whatsapp
            settings.contact_email = contact_email
            settings.business_hours = business_hours
            settings.social_links = social_links

        db.session.commit()
        flash('Site settings updated', 'success')
        return redirect(url_for('admin_site_settings'))

    return render_template('admin/site_settings.html', settings=settings)

@app.route('/admin/products')
@login_required
def admin_products():
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    # Load products and compute simple stats for the admin products view
    products = Product.query.order_by(Product.created_at.desc()).all()
    available_products = Product.query.filter_by(is_available=True).count()
    male_puppies = Product.query.filter(Product.gender.in_(['Male', 'male', 'M', 'm'])).count()
    female_puppies = Product.query.filter(Product.gender.in_(['Female', 'female', 'F', 'f'])).count()
    total_value = sum([p.price or 0 for p in products])

    return render_template('admin/products.html', 
                           products=products,
                           available_products=available_products,
                           male_puppies=male_puppies,
                           female_puppies=female_puppies,
                           total_value=total_value)

@app.route('/admin/product/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Handle multiple file uploads
        image_files = request.files.getlist('images')
        image_urls = []
        for image_file in image_files:
            if image_file and allowed_file(image_file.filename):
                filename = secure_filename(image_file.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image_file.save(image_path)
                image_urls.append(f'uploads/{filename}')
        
        # Normalize breed (trim/case) and process additional details
        raw_breed = request.form.get('breed')
        breed = None
        if raw_breed:
            breed = raw_breed.strip()
            if breed:
                breed = breed.title()

        # Process additional details
        additional_details = {}
        details_keys = request.form.getlist('detail_key[]')
        details_values = request.form.getlist('detail_value[]')
        
        for key, value in zip(details_keys, details_values):
            if key and value:
                additional_details[key] = value
        
        product = Product(
            name=request.form.get('name'),
            breed=breed,
            gender=request.form.get('gender'),
            age=request.form.get('age'),
            price=float(request.form.get('price')),
            rating=float(request.form.get('rating') or 0.0),
            description=request.form.get('description'),
            image_urls=image_urls,
            additional_details=additional_details
        )
        
        db.session.add(product)
        db.session.commit()
        
        flash('Product added successfully', 'success')
        return redirect(url_for('admin_products'))
    
    # pass existing breeds for suggestions (clean, unique, sorted)
    raw_breeds = [b[0] for b in db.session.query(Product.breed).all() if b[0]]
    cleaned = []
    for r in raw_breeds:
        if not r:
            continue
        c = r.strip().title()
        if c and c not in cleaned:
            cleaned.append(c)
    return render_template('admin/add_product.html', breeds=cleaned)

@app.route('/admin/product/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        product.name = request.form.get('name')
        # Normalize breed input
        raw_breed = request.form.get('breed')
        if raw_breed:
            b = raw_breed.strip()
            product.breed = b.title() if b else None
        else:
            product.breed = None
        product.gender = request.form.get('gender')
        product.age = request.form.get('age')
        product.price = float(request.form.get('price'))
        # rating (0.0 - 5.0)
        try:
            product.rating = float(request.form.get('rating') or 0.0)
        except Exception:
            product.rating = 0.0
        product.description = request.form.get('description')
        
        # Handle file upload
        # allow adding more images; keep existing ones
        image_files = request.files.getlist('images')
        if image_files:
            existing = product.image_urls or []
            for image_file in image_files:
                if image_file and allowed_file(image_file.filename):
                    filename = secure_filename(image_file.filename)
                    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    image_file.save(image_path)
                    existing.append(f'uploads/{filename}')
            product.image_urls = existing
        
        # Process additional details
        additional_details = {}
        details_keys = request.form.getlist('detail_key[]')
        details_values = request.form.getlist('detail_value[]')
        
        for key, value in zip(details_keys, details_values):
            if key and value:
                additional_details[key] = value
        
        product.additional_details = additional_details
        
        db.session.commit()
        flash('Product updated successfully', 'success')
        return redirect(url_for('admin_products'))
    
    raw_breeds = [b[0] for b in db.session.query(Product.breed).all() if b[0]]
    cleaned = []
    for r in raw_breeds:
        if not r:
            continue
        c = r.strip().title()
        if c and c not in cleaned:
            cleaned.append(c)
    return render_template('admin/edit_product.html', product=product, breeds=cleaned)

@app.route('/admin/product/delete/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    
    return jsonify({'success': True})


@app.route('/admin/product/<int:product_id>/delete-image', methods=['POST'])
@login_required
def delete_product_image(product_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403

    product = Product.query.get_or_404(product_id)
    data = request.get_json() or {}
    filename = data.get('filename')
    if not filename:
        return jsonify({'success': False, 'message': 'No filename provided'}), 400

    imgs = product.image_urls or []
    if isinstance(imgs, str):
        imgs_list = [i for i in imgs.split(',') if i]
    else:
        imgs_list = list(imgs)

    if filename not in imgs_list:
        return jsonify({'success': False, 'message': 'Image not found on product'}), 404

    imgs_list.remove(filename)
    if isinstance(imgs, str):
        product.image_urls = ','.join(imgs_list)
    else:
        product.image_urls = imgs_list

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Database update failed'}), 500

    # Delete file from disk
    try:
        file_path = os.path.join(app.root_path, 'static', filename)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print('Failed to remove file:', e)

    return jsonify({'success': True})

@app.route('/admin/orders')
@login_required
def admin_orders():
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)

@app.route('/admin/order/<int:order_id>')
@login_required
def view_order(order_id):
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    order = Order.query.get_or_404(order_id)
    return render_template('admin/view_order.html', order=order)

@app.route('/admin/order/update_status/<int:order_id>', methods=['POST'])
@login_required
def update_order_status(order_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    order = Order.query.get_or_404(order_id)
    new_status = request.json.get('status')
    
    if new_status in ['pending', 'processing', 'completed', 'cancelled']:
        order.status = new_status
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'error': 'Invalid status'}), 400


@app.route('/admin/order/update_payment/<int:order_id>', methods=['POST'])
@login_required
def update_order_payment_status(order_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403

    order = Order.query.get_or_404(order_id)
    new_status = request.json.get('payment_status')

    if new_status in ['pending', 'paid', 'refunded']:
        order.payment_status = new_status
        db.session.commit()
        return jsonify({'success': True})

    return jsonify({'error': 'Invalid payment status'}), 400

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create admin user if not exists
        if not User.query.filter_by(username=app.config.get('ADMIN_USERNAME')).first():
            # Determine a safe admin email: prefer ADMIN_EMAIL, then CONTACT_EMAIL, then a generated default
            admin_email = app.config.get('ADMIN_EMAIL') or app.config.get('CONTACT_EMAIL')
            if not admin_email:
                admin_username = app.config.get('ADMIN_USERNAME') or 'admin'
                admin_email = f"{admin_username}@gmail.com"

            admin = User(
                username=app.config.get('ADMIN_USERNAME') or 'admin',
                email=admin_email,
                is_admin=True
            )
            # Ensure an admin password exists; if not, use a fallback and log a warning
            admin_password = app.config.get('ADMIN_PASSWORD') or 'change_me'
            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.commit()
    # Use configurable host/port from config; default port 5000
    host = app.config.get('HOST', '0.0.0.0')
    port = int(app.config.get('PORT'))
    app.run(host=host, port=port, debug=True)