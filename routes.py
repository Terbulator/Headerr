import os
import hmac
import hashlib

from flask import render_template, request, redirect, url_for, session, flash
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename

from app import app, db
from models import Jersey, User, Order, get_settings

ALLOWED_CATEGORIES = ["National", "Club", "Retro", "General"]


def admin_required(view):
    from functools import wraps

    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin():
            flash("You do not have permission to access that page.", "error")
            return redirect(url_for("index"))
        return view(*args, **kwargs)

    return wrapped


@app.route("/")
def index():
    active_category = request.args.get("category")
    store = get_settings()

    if active_category in ALLOWED_CATEGORIES:
        jerseys = Jersey.query.filter_by(category=active_category).all()
    else:
        jerseys = Jersey.query.all()
        active_category = None

    return render_template(
        "catalog.html",
        jerseys=jerseys,
        store=store,
        active_category=active_category,
    )


def build_cart():
    cart = session.get("cart", [])
    items = []
    total = 0.0
    for jersey_id in cart:
        jersey = Jersey.query.get(jersey_id)
        if jersey:
            items.append({"jersey": jersey, "quantity": 1, "subtotal": jersey.price})
            total += jersey.price
    return items, total


@app.route("/cart")
def view_cart():
    cart_items, total = build_cart()
    return render_template("cart.html", cart_items=cart_items, total=total)


@app.route("/add_to_cart/<int:jersey_id>", methods=["POST"])
def add_to_cart(jersey_id):
    if Jersey.query.get(jersey_id) is None:
        flash("Product not found.", "error")
        return redirect(url_for("index"))
    cart = session.get("cart", [])
    cart.append(jersey_id)
    session["cart"] = cart
    return redirect(request.referrer or url_for("index"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        if not name or not email or not password:
            flash("All fields are required.", "error")
        elif User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "error")
        else:
            user = User(name=name, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("index"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/admin", methods=["GET", "POST"])
@admin_required
def admin_orders():
    store = get_settings()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        price = request.form.get("price")
        category = request.form.get("category", "National")
        file = request.files.get("image")

        if not name or not price:
            flash("Name and price are required.", "error")
        else:
            try:
                price = float(price)
            except ValueError:
                flash("Price must be a number.", "error")
                return redirect(url_for("admin_orders"))

            image_file = "default.jpg"
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                image_file = filename

            if category not in ALLOWED_CATEGORIES:
                category = "National"

            jersey = Jersey(
                name=name,
                price=price,
                category=category,
                image_file=image_file,
            )
            db.session.add(jersey)
            db.session.commit()
            flash("Kit published to store!", "success")
        return redirect(url_for("admin_orders"))

    jerseys = Jersey.query.order_by(Jersey.id.desc()).all()
    orders = Order.query.order_by(Order.id.desc()).all()
    return render_template(
        "admin.html", jerseys=jerseys, orders=orders, store=store
    )


@app.route("/admin/update_settings", methods=["POST"])
@admin_required
def update_settings():
    store = get_settings()
    store.store_name = request.form.get("store_name", "Headerr Store").strip()
    store.announcement_text = request.form.get("announcement_text", "").strip()
    store.theme_color = request.form.get("theme_color", "black")
    store.show_retro = "True" if request.form.get("show_retro") else "False"
    db.session.commit()
    flash("Interface settings updated.", "success")
    return redirect(url_for("admin_orders"))


@app.route("/admin/delete_jersey/<int:jersey_id>", methods=["POST"])
@admin_required
def delete_jersey(jersey_id):
    jersey = Jersey.query.get_or_404(jersey_id)
    db.session.delete(jersey)
    db.session.commit()
    flash("Kit deleted.", "success")
    return redirect(url_for("admin_orders"))


@app.route("/admin/edit_jersey/<int:jersey_id>", methods=["GET", "POST"])
@admin_required
def edit_jersey(jersey_id):
    jersey = Jersey.query.get_or_404(jersey_id)
    if request.method == "POST":
        jersey.name = request.form.get("name", jersey.name).strip()
        try:
            jersey.price = float(request.form.get("price", jersey.price))
        except ValueError:
            flash("Price must be a number.", "error")
            return redirect(url_for("edit_jersey", jersey_id=jersey.id))
        category = request.form.get("category", jersey.category)
        if category in ALLOWED_CATEGORIES:
            jersey.category = category
        db.session.commit()
        flash("Kit updated.", "success")
        return redirect(url_for("admin_orders"))
    return render_template("edit_jersey.html", jersey=jersey)


@app.route("/admin/update_order/<int:order_id>", methods=["POST"])
@admin_required
def update_order(order_id):
    order = Order.query.get_or_404(order_id)
    status = request.form.get("status")
    if status in ("Pending", "Shipped", "Delivered"):
        order.status = status
        db.session.commit()
    return redirect(url_for("admin_orders"))


@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cart_items, total = build_cart()
    if request.method == "POST":
        address = request.form.get("address", "").strip()
        if not cart_items:
            flash("Your cart is empty.", "error")
            return redirect(url_for("view_cart"))
        if not address:
            flash("Please provide a delivery address.", "error")
            return render_template("checkout.html", cart_items=cart_items, total=total)

        order = Order(
            customer_id=current_user.id,
            address=address,
            amount_paid=total,
        )
        db.session.add(order)
        db.session.commit()
        session["cart"] = []
        return redirect(url_for("order_confirmed", order_id=order.id))

    return render_template("checkout.html", cart_items=cart_items, total=total)


@app.route("/order-confirmed")
@login_required
def order_confirmed():
    order_id = request.args.get("order_id", type=int)
    order = Order.query.filter_by(id=order_id, customer_id=current_user.id).first_or_404()
    return render_template("success.html", order=order)


@app.route("/create-order")
@login_required
def create_order():
    if not (app.config["RAZORPAY_KEY_ID"] and app.config["RAZORPAY_KEY_SECRET"]):
        return "Razorpay is not configured. Basic checkout is available at /checkout."
    return "Razorpay order creation is not implemented yet."


@app.route("/verify-payment", methods=["POST"])
@login_required
def verify_payment():
    return "Payment verification is not implemented yet."
