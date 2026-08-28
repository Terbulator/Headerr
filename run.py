from app import app, db
import routes

if __name__ == '__main__':
    # This creates the DB file automatically if it doesn't exist
    with app.app_context():
        db.create_all()
    app.run(debug=True)