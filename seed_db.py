from app import app
from models import db, Jersey, User, StoreSettings

with app.app_context():
    # First, we clear out the old test data so we have a clean slate
    db.drop_all()
    db.create_all()

    # Create your new real inventory
    kit_1 = Jersey(
        name="MBSG Home Kit",
        description="Authentic Maroon and Green",
        price=90.00,
        category="Club",
        image_file="default.jpg"
    )

    kit_2 = Jersey(
        name="Argentina 3-Star Home",
        description="Official Match Jersey",
        price=120.00,
        category="National",
        image_file="argentina.png"
    )

    kit_3 = Jersey(
        name="HEADERR Blackout Concept",
        description="Limited Edition Pre-season Drop",
        price=150.00,
        category="Club",
        image_file="blackout.png"
    )

    # Ensure a settings row exists
    if StoreSettings.query.get(1) is None:
        db.session.add(StoreSettings(id=1))

    db.session.add_all([kit_1, kit_2, kit_3])
    db.session.commit()

    print("Success! The MBSG and Argentina kits are now in the database.")