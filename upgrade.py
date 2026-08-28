from sqlalchemy import inspect

from app import app
from models import StoreSettings, db

with app.app_context():
    db.create_all()
    inspector = inspect(db.engine)
    columns = {col["name"] for col in inspector.get_columns("order")}

    with db.engine.begin() as conn:
        if "payment_method" not in columns:
            conn.exec_driver_sql(
                "ALTER TABLE \"order\" ADD COLUMN payment_method VARCHAR(20) NOT NULL DEFAULT 'COD'"
            )
            print("Added column order.payment_method")
        if "payment_status" not in columns:
            conn.exec_driver_sql(
                "ALTER TABLE \"order\" ADD COLUMN payment_status VARCHAR(20) NOT NULL DEFAULT 'COD'"
            )
            print("Added column order.payment_status")
        if "payment_id" not in columns:
            conn.exec_driver_sql(
                "ALTER TABLE \"order\" ADD COLUMN payment_id VARCHAR(100)"
            )
            print("Added column order.payment_id")

    if StoreSettings.query.get(1) is None:
        db.session.add(StoreSettings(id=1))
        db.session.commit()

    print("Database successfully upgraded with OrderItem and payment columns!")