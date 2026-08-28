import os
import secrets

from dotenv import load_dotenv
from flask import Flask, abort, request, session
from flask_login import LoginManager
from models import db, get_settings

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

load_dotenv(os.path.join(BASE_DIR, ".env"))

app = Flask(__name__)

# Vercel's deployed filesystem is read-only.
# Only /tmp is writable.
if os.environ.get("VERCEL"):
    INSTANCE_DIR = "/tmp/instance"
    UPLOAD_DIR = "/tmp/images"
else:
    INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
    UPLOAD_DIR = os.path.join(BASE_DIR, "static", "images")

os.makedirs(INSTANCE_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Database
database_url = os.environ.get("DATABASE_URL")

if database_url:
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "sqlite:///" + os.path.join(INSTANCE_DIR, "headerr.db")
    )

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "dev-secret-key"
)

app.config["ADMIN_EMAIL"] = os.environ.get("ADMIN_EMAIL", "")

app.config["UPLOAD_FOLDER"] = UPLOAD_DIR

app.config["RAZORPAY_KEY_ID"] = os.environ.get(
    "RAZORPAY_KEY_ID",
    ""
)

app.config["RAZORPAY_KEY_SECRET"] = os.environ.get(
    "RAZORPAY_KEY_SECRET",
    ""
)

db.init_app(app)



login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))


def get_csrf_token():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(32)
    return session["_csrf_token"]


def cart_count():
    cart = session.get("cart", {})
    if isinstance(cart, list):
        return len(cart)
    return sum(v for v in cart.values() if isinstance(v, int))


@app.before_request
def csrf_protect():
    if request.method == "POST":
        token = request.form.get("_csrf_token", "")
        if not token or not secrets.compare_digest(
            token, session.get("_csrf_token", "")
        ):
            abort(400)


@app.context_processor
def inject_store():
    return {
        "store": get_settings(),
        "csrf_token": get_csrf_token,
        "cart_count": cart_count,
    }