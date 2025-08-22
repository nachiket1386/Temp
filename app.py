import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///lams.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Register blueprints
from auth import auth_bp
from views import views_bp

app.register_blueprint(auth_bp)
app.register_blueprint(views_bp)

with app.app_context():
    # Import models to ensure tables are created
    import models
    db.create_all()
    
    # Create default master user if not exists
    from models import User, UserRole
    from werkzeug.security import generate_password_hash
    
    master_user = User.query.filter_by(username='master').first()
    if not master_user:
        master_user = User(
            username='master',
            role=UserRole.MASTER,
            password_hash=generate_password_hash('master123'),
            is_active=True,
            must_change_password=False
        )
        db.session.add(master_user)
        db.session.commit()
        logging.info("Created default master user (username: master, password: master123)")
