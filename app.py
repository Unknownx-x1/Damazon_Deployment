from flask import Flask, render_template, request, redirect, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db, login_manager
import os

# 🔥 NEW: dotenv + Gemini
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

app = Flask(__name__)

# -------------------------
# Configuration
# -------------------------
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "damazon-secret-key")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Gemini Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")
else:
    model = None

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = "login"

# Import models AFTER db init
from models import User, Product, Order, Cart


# -------------------------
# USER LOADER
# -------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# -------------------------
# HOME
# -------------------------
@app.route("/")
def home():
    return render_template("landing.html")


# -------------------------
# SIGNUP
# -------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get("role")

        if User.query.filter_by(username=username).first():
            return "Username already exists!"

        hashed_password = generate_password_hash(password)

        new_user = User(
            username=username,
            password=hashed_password,
            role=role
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("signup.html")


# -------------------------
# LOGIN
# -------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)

            if user.role == "seller":
                return redirect(url_for("seller_dashboard"))
            else:
                return redirect(url_for("damazon"))

        return "Invalid username or password"

    return render_template("login.html")


# -------------------------
# BUYER MARKETPLACE
# -------------------------
@app.route("/damazon")
@login_required
def damazon():
    if current_user.role != "buyer":
        return "Access denied"

    search_query = request.args.get("search")

    if search_query:
        products = Product.query.filter(
            Product.name.ilike(f"%{search_query}%")
        ).all()
    else:
        products = Product.query.all()

    return render_template("damazon.html", products=products)


# -------------------------
# ADD TO CART
# -------------------------
@app.route("/add-to-cart/<int:product_id>")
@login_required
def add_to_cart(product_id):

    if current_user.role != "buyer":
        return "Access denied"

    product = Product.query.get(product_id)

    if not product or product.stock <= 0:
        return "Product unavailable"

    existing_item = Cart.query.filter_by(
        buyer_id=current_user.id,
        product_id=product.id
    ).first()

    if existing_item:
        existing_item.quantity += 1
    else:
        db.session.add(Cart(
            quantity=1,
            buyer_id=current_user.id,
            product_id=product.id
        ))

    db.session.commit()

    return redirect(url_for("damazon"))


# -------------------------
# CART
# -------------------------
@app.route("/cart")
@login_required
def cart():
    if current_user.role != "buyer":
        return "Access denied"

    cart_items = Cart.query.filter_by(
        buyer_id=current_user.id
    ).all()

    return render_template("cart.html", cart_items=cart_items)


# -------------------------
# CHECKOUT PAGE
# -------------------------
@app.route("/checkout")
@login_required
def checkout():

    if current_user.role != "buyer":
        return "Access denied"

    cart_items = Cart.query.filter_by(
        buyer_id=current_user.id
    ).all()

    if not cart_items:
        return redirect(url_for("cart"))

    total = sum(item.product.price * item.quantity for item in cart_items)

    return render_template("payment.html", total=total)


# -------------------------
# PROCESS PAYMENT (MOCK)
# -------------------------
@app.route("/process-payment")
@login_required
def process_payment():

    cart_items = Cart.query.filter_by(
        buyer_id=current_user.id
    ).all()

    for item in cart_items:
        if item.product.stock >= item.quantity:

            item.product.stock -= item.quantity

            db.session.add(Order(
                quantity=item.quantity,
                buyer_id=current_user.id,
                product_id=item.product.id,
                status="Pending"
            ))

    Cart.query.filter_by(buyer_id=current_user.id).delete()
    db.session.commit()

    return redirect(url_for("payment_success"))


# -------------------------
# PAYMENT SUCCESS
# -------------------------
@app.route("/payment-success")
@login_required
def payment_success():
    return render_template("payment_success.html")


# -------------------------
# MY ORDERS
# -------------------------
@app.route("/my-orders")
@login_required
def my_orders():
    if current_user.role != "buyer":
        return "Access denied"

    orders = Order.query.filter_by(
        buyer_id=current_user.id
    ).all()

    return render_template("my_orders.html", orders=orders)


# -------------------------
# SELLER DASHBOARD
# -------------------------
@app.route("/seller-dashboard")
@login_required
def seller_dashboard():

    if current_user.role != "seller":
        return "Access denied"

    seller_products = Product.query.filter_by(
        seller_id=current_user.id
    ).all()

    seller_orders = Order.query.join(Product).filter(
        Product.seller_id == current_user.id
    ).all()

    return render_template(
        "seller_dashboard.html",
        products=seller_products,
        orders=seller_orders
    )


# -------------------------
# UPDATE ORDER STATUS
# -------------------------
@app.route("/update-order/<int:order_id>/<string:new_status>")
@login_required
def update_order(order_id, new_status):

    if current_user.role != "seller":
        return "Access denied"

    order = Order.query.get(order_id)

    if not order or order.product.seller_id != current_user.id:
        return "Unauthorized"

    order.status = new_status
    db.session.commit()

    return redirect(url_for("seller_dashboard"))


# -------------------------
# ADD PRODUCT
# -------------------------
@app.route("/add-product", methods=["GET", "POST"])
@login_required
def add_product():

    if current_user.role != "seller":
        return "Access denied"

    if request.method == "POST":

        name = request.form.get("name")
        price = float(request.form.get("price"))
        stock = int(request.form.get("stock"))

        image_file = request.files.get("image")
        filename = None

        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)

            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])

            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)

        db.session.add(Product(
            name=name,
            price=price,
            stock=stock,
            seller_id=current_user.id,
            image=filename
        ))

        db.session.commit()
        return redirect(url_for("seller_dashboard"))

    return render_template("add_product.html")


# -------------------------
# DELETE PRODUCT
# -------------------------
@app.route("/delete-product/<int:product_id>")
@login_required
def delete_product(product_id):

    if current_user.role != "seller":
        return "Access denied"

    product = Product.query.get(product_id)

    if not product or product.seller_id != current_user.id:
        return "Unauthorized"

    Cart.query.filter_by(product_id=product.id).delete()
    Order.query.filter_by(product_id=product.id).delete()

    db.session.delete(product)
    db.session.commit()

    return redirect(url_for("seller_dashboard"))


# -------------------------
# GEMINI CHATBOT API
# -------------------------
@app.route("/chatbot", methods=["POST"])
@login_required
def chatbot():

    if current_user.role != "buyer":
        return jsonify({"error": "Access denied"}), 403

    if not model:
        return jsonify({"reply": "AI service not configured."})

    user_message = request.json.get("message")

    prompt = f"""
    You are an agricultural product assistant.
    Answer clearly and briefly.

    User question:
    {user_message}
    """

    response = model.generate_content(prompt)

    return jsonify({"reply": response.text})


# -------------------------
# LOGOUT
# -------------------------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)