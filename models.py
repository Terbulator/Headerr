from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class Jersey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(500))
    price = db.Column(db.Float, nullable=False, default=0.0)
    category = db.Column(db.String(50), nullable=False, default="National")
    image_file = db.Column(db.String(255), nullable=False, default="default.jpg")


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        from app import app
        return self.email and self.email == app.config.get("ADMIN_EMAIL")


class StoreSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    store_name = db.Column(db.String(100), nullable=False, default="Headerr Store")
    announcement_text = db.Column(db.String(255), nullable=False, default="Free shipping on orders over Rs. 999")
    theme_color = db.Column(db.String(20), nullable=False, default="black")
    show_retro = db.Column(db.String(5), nullable=False, default="True")


def get_settings():
    settings = StoreSettings.query.get(1)
    if settings is None:
        settings = StoreSettings(id=1)
        db.session.add(settings)
        db.session.commit()
    return settings


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), nullable=False, default="Pending")
    payment_id = db.Column(db.String(100))
    amount_paid = db.Column(db.Float, nullable=False, default=0.0)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    customer = db.relationship("User", backref="orders")
