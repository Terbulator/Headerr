from app import app
import routes

with app.app_context():
    for rule in app.url_map.iter_rules():
        print(f"URL: {rule.rule} | Endpoint: {rule.endpoint}")