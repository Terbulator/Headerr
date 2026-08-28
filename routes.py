import hashlib
import hmac
import os

import razorpay
from flask import flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.utils import secure_filename

from app import app, db
from models import Jersey, Order, OrderItem, User, get_settings

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


def get_cart():
    cart = session.get("cart", {})
    if isinstance(cart, list):
        new_cart = {}
        for jersey_id in cart:
            key = str(jersey_id)
            new_cart[key] = new_cart.get(key, 0) + 1
        session["cart"] = new_cart
        return new_cart
    return cart


def build_cart():
    cart = get_cart()
    items = []
    total = 0.0
    for raw_id, quantity in cart.items():
        try:
            jersey_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        jersey = Jersey.query.get(jersey_id)
        if jersey and isinstance(quantity, int) and quantity > 0:
            subtotal = jersey.price * quantity
            items.append(
                {"jersey": jersey, "quantity": quantity, "subtotal": subtotal}
            )
            total += subtotal
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
    cart = get_cart()
    key = str(jersey_id)
    cart[key] = int(cart.get(key, 0)) + 1
    session["cart"] = cart
    return redirect(request.referrer or url_for("index"))


@app.route("/update_cart/<int:jersey_id>", methods=["POST"])
def update_cart(jersey_id):
    if Jersey.query.get(jersey_id) is None:
        flash("Product not found.", "error")
        return redirect(url_for("view_cart"))
    quantity = request.form.get("quantity", type=int, default=1)
    cart = get_cart()
    key = str(jersey_id)
    if quantity and quantity > 0:
        cart[key] = min(quantity, 99)
    else:
        cart.pop(key, None)
    session["cart"] = cart
    return redirect(url_for("view_cart"))


@app.route("/remove_from_cart/<int:jersey_id>", methods=["POST"])
def remove_from_cart(jersey_id):
    cart = get_cart()
    cart.pop(str(jersey_id), None)
    session["cart"] = cart
    return redirect(url_for("view_cart"))


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


def remove_image_file(filename):
    if not filename or filename in ("default.jpg", "placeholder.svg"):
        return
    if Jersey.query.filter_by(image_file=filename).first():
        return
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


@app.route("/admin/delete_jersey/<int:jersey_id>", methods=["POST"])
@admin_required
def delete_jersey(jersey_id):
    jersey = Jersey.query.get_or_404(jersey_id)
    filename = jersey.image_file
    db.session.delete(jersey)
    db.session.commit()
    remove_image_file(filename)
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
        file = request.files.get("image")
        if file and file.filename:
            old_file = jersey.image_file
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            jersey.image_file = filename
            db.session.flush()
            remove_image_file(old_file)
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
        payment_method = request.form.get("payment_method", "COD")
        if not cart_items:
            flash("Your cart is empty.", "error")
            return redirect(url_for("view_cart"))
        if not address:
            flash("Please provide a delivery address.", "error")
            return render_template(
                "checkout.html", cart_items=cart_items, total=total
            )

        is_online = payment_method == "razorpay"
        if is_online and not (
            app.config["RAZORPAY_KEY_ID"] and app.config["RAZORPAY_KEY_SECRET"]
        ):
            flash(
                "Online payment is not configured. Please choose Cash on Delivery.",
                "error",
            )
            return render_template(
                "checkout.html", cart_items=cart_items, total=total
            )

        order = Order(
            customer_id=current_user.id,
            address=address,
            amount_paid=total,
            payment_method="Online" if is_online else "COD",
            payment_status="Pending" if is_online else "COD",
            status="Pending",
        )
        db.session.add(order)
        db.session.flush()
        for item in cart_items:
            db.session.add(
                OrderItem(
                    order_id=order.id,
                    jersey_id=item["jersey"].id,
                    quantity=item["quantity"],
                    unit_price=item["jersey"].price,
                )
            )
        db.session.commit()
        session["cart"] = {}

        if is_online:
            client = razorpay.Client(
                auth=(
                    app.config["RAZORPAY_KEY_ID"],
                    app.config["RAZORPAY_KEY_SECRET"],
                )
            )
            rzp_order = client.order.create(
                {
                    "amount": int(total * 100),
                    "currency": "INR",
                    "receipt": f"store_order_{order.id}",
                    "payment_capture": 1,
                }
            )
            session["pending_razorpay"] = {
                "order_id": order.id,
                "razorpay_order_id": rzp_order["id"],
            }
            return redirect(url_for("pay"))

        return redirect(url_for("order_confirmed", order_id=order.id))

    return render_template("checkout.html", cart_items=cart_items, total=total)


@app.route("/order-confirmed")
@login_required
def order_confirmed():
    order_id = request.args.get("order_id", type=int)
    order = Order.query.filter_by(
        id=order_id, customer_id=current_user.id
    ).first_or_404()
    return render_template("success.html", order=order)


@app.route("/pay")
@login_required
def pay():
    pending = session.get("pending_razorpay")
    if not pending:
        flash("No pending payment found.", "error")
        return redirect(url_for("view_cart"))
    order = Order.query.filter_by(
        id=pending["order_id"], customer_id=current_user.id
    ).first_or_404()
    store = get_settings()
    return render_template(
        "razorpay_checkout.html",
        key_id=app.config["RAZORPAY_KEY_ID"],
        amount=str(int(order.amount_paid * 100)),
        order_id=pending["razorpay_order_id"],
        user=current_user,
        store=store,
    )


@app.route("/verify-payment", methods=["POST"])
@login_required
def verify_payment():
    pending = session.get("pending_razorpay")
    if not pending:
        flash("No pending payment found.", "error")
        return redirect(url_for("view_cart"))

    payment_id = request.form.get("razorpay_payment_id", "")
    rzp_order_id = request.form.get("razorpay_order_id", "")
    signature = request.form.get("razorpay_signature", "")

    secret = app.config["RAZORPAY_KEY_SECRET"].encode()
    expected = hmac.new(
        secret, f"{rzp_order_id}|{payment_id}".encode(), hashlib.sha256
    ).hexdigest()

    order = Order.query.filter_by(
        id=pending["order_id"], customer_id=current_user.id
    ).first()
    if not order or not hmac.compare_digest(expected, signature):
        flash(
            "Payment verification failed. Please try again or contact support.",
            "error",
        )
        return redirect(url_for("pay"))

    session.pop("pending_razorpay", None)
    order.payment_status = "Paid"
    order.payment_id = payment_id
    db.session.commit()
    return redirect(url_for("order_confirmed", order_id=order.id))