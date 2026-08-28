from app import app
import routes  # noqa: F401  registers all routes on the app

if __name__ == "__main__":
    app.run()