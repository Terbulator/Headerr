from app import app, db
from models import Jersey

with app.app_context():
    Jersey.query.delete()

    j1 = Jersey(name="Messi Argentina 2026 Home Kit", price=299.00, category="National", image_file="argentina.png")
    j2 = Jersey(name="Mohun Bagan SG 2025 Home Kit", price=399.00, category="Club", image_file="default.jpg")
    j3 = Jersey(name="Ronaldo Man United 2008 UCL", price=349.00, category="Retro", image_file="default.jpg")
    j4 = Jersey(name="Barcelona 2009 Home Kit", price=249.00, category="Retro", image_file="default.jpg")
    j5 = Jersey(name="Brazil 2002 World Cup Kit", price=450.00, category="National", image_file="blackout.png")

    db.session.add_all([j1, j2, j3, j4, j5])
    db.session.commit()
    print("Database Seeded Successfully!")
