from app import app, db
from models import StoreSettings

with app.app_context():
    print("Dropping old cloud tables...")
    db.drop_all()
    print("Creating new upgraded tables...")
    db.create_all()
    db.session.add(StoreSettings(id=1))
    db.session.commit()
    print("Cloud Database Reset Complete!")