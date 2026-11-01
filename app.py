import os
from functools import wraps

import mysql.connector
from dotenv import load_dotenv
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-development-secret")

DATABASE_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "online_shop"),
}

STARTER_PRODUCTS = [
    ("Ceramic Coffee Mug", 14.00, "https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?auto=format&fit=crop&w=900&q=85"),
    ("Canvas Everyday Tote", 22.50, "https://images.unsplash.com/photo-1590874103328-eac38a683ce7?auto=format&fit=crop&w=900&q=85"),
    ("Desk Notebook", 12.00, "https://images.unsplash.com/photo-1531346878377-a5be20888e57?auto=format&fit=crop&w=900&q=85"),
    ("Glass Water Bottle", 18.00, "https://images.unsplash.com/photo-1602143407151-7111542de6e8?auto=format&fit=crop&w=900&q=85"),
]


def get_db():
    """Open a MySQL connection using the environment configuration."""
    return mysql.connector.connect(**DATABASE_CONFIG)


def initialize_database():
    """Create the required tables and add starter products once."""
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS products (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(150) NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            image_url VARCHAR(500) NOT NULL
        )"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS orders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            customer_name VARCHAR(100) NOT NULL,
            shipping_address TEXT NOT NULL,
            total DECIMAL(10, 2) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS order_items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            order_id INT NOT NULL,
            product_id INT NOT NULL,
            quantity INT NOT NULL,
            unit_price DECIMAL(10, 2) NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )"""
    )
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO products (name, price, image_url) VALUES (%s, %s, %s)",
            STARTER_PRODUCTS,
        )
    connection.commit()
    cursor.close()
    connection.close()


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in before checkout.", "info")
            return redirect(url_for("login", next=url_for("checkout")))
        return view(*args, **kwargs)

    return wrapped_view


def cart_products():
    """Return the current cart's product rows, quantities, and total."""
    cart = session.get("cart", {})
    if not cart:
        return [], 0.0

    product_ids = [int(product_id) for product_id in cart]
    placeholders = ", ".join(["%s"] * len(product_ids))
    connection = get_db()
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        f"SELECT id, name, price, image_url FROM products WHERE id IN ({placeholders})",
        product_ids,
    )
    products = cursor.fetchall()
    cursor.close()
    connection.close()

    items = []
    total = 0.0
    for product in products:
        quantity = int(cart.get(str(product["id"]), 0))
        product["quantity"] = quantity
        product["subtotal"] = float(product["price"]) * quantity
        total += product["subtotal"]
        items.append(product)
    return items, total


@app.context_processor
def inject_cart_count():
    return {"cart_count": sum(int(quantity) for quantity in session.get("cart", {}).values())}


@app.route("/")
@app.route("/products")
def index():
    search = request.args.get("q", "").strip()
    connection = get_db()
    cursor = connection.cursor(dictionary=True)
    if search:
        cursor.execute(
            "SELECT id, name, price, image_url FROM products WHERE name LIKE %s ORDER BY id",
            (f"%{search}%",),
        )
    else:
        cursor.execute("SELECT id, name, price, image_url FROM products ORDER BY id")
    products = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template("index.html", products=products, search=search)


@app.post("/cart/add/<int:product_id>")
def add_to_cart(product_id):
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM products WHERE id = %s", (product_id,))
    product_exists = cursor.fetchone() is not None
    cursor.close()
    connection.close()
    if not product_exists:
        flash("That product could not be found.", "error")
        return redirect(url_for("index"))

    cart = session.get("cart", {})
    product_key = str(product_id)
    cart[product_key] = int(cart.get(product_key, 0)) + 1
    session["cart"] = cart
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify(cart_count=sum(cart.values()))
    flash("Product added to your cart.", "success")
    return redirect(request.referrer or url_for("index"))


@app.route("/cart")
def view_cart():
    items, total = cart_products()
    return render_template("cart.html", items=items, total=total)


@app.post("/cart/update/<int:product_id>")
def update_cart(product_id):
    try:
        quantity = int(request.form.get("quantity", "1"))
    except ValueError:
        quantity = 1
    cart = session.get("cart", {})
    if quantity <= 0:
        cart.pop(str(product_id), None)
    elif str(product_id) in cart:
        cart[str(product_id)] = min(quantity, 99)
    session["cart"] = cart
    return redirect(url_for("view_cart"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 8:
            flash("Enter your name and email, and use a password of at least 8 characters.", "error")
            return render_template("register.html")
        connection = get_db()
        cursor = connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
                (name, email, generate_password_hash(password)),
            )
            connection.commit()
            user_id = cursor.lastrowid
        except mysql.connector.IntegrityError:
            flash("An account with that email already exists.", "error")
            return render_template("register.html")
        finally:
            cursor.close()
            connection.close()
        cart = session.get("cart", {})
        session.clear()
        session["user_id"] = user_id
        session["user_name"] = name
        session["cart"] = cart
        flash("Your account is ready.", "success")
        return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        connection = get_db()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id, name, password_hash FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        connection.close()
        if user and check_password_hash(user["password_hash"], password):
            cart = session.get("cart", {})
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["cart"] = cart
            destination = request.args.get("next")
            return redirect(destination if destination and destination.startswith("/") else url_for("index"))
        flash("Email or password is incorrect.", "error")
    return render_template("login.html")


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    items, total = cart_products()
    if not items:
        flash("Your cart is empty.", "info")
        return redirect(url_for("view_cart"))
    if request.method == "POST":
        customer_name = request.form.get("customer_name", "").strip()
        shipping_address = request.form.get("shipping_address", "").strip()
        if not customer_name or not shipping_address:
            flash("Enter a name and shipping address to continue.", "error")
            return render_template("checkout.html", items=items, total=total)

        connection = get_db()
        cursor = connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO orders (user_id, customer_name, shipping_address, total) VALUES (%s, %s, %s, %s)",
                (session["user_id"], customer_name, shipping_address, total),
            )
            order_id = cursor.lastrowid
            cursor.executemany(
                "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (%s, %s, %s, %s)",
                [
                    (order_id, item["id"], item["quantity"], item["price"])
                    for item in items
                ],
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()
        session["cart"] = {}
        return render_template("order_success.html", order_id=order_id)
    return render_template("checkout.html", items=items, total=total)


if __name__ == "__main__":
    initialize_database()
    app.run(debug=os.getenv("FLASK_DEBUG", "true").lower() == "true")