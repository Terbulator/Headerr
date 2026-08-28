from app import app
from models import db, StoreSettings

with app.app_context():
    db.create_all()
    if StoreSettings.query.get(1) is None:
        db.session.add(StoreSettings(id=1))
        db.session.commit()
    print("Database successfully upgraded with Order tables!")