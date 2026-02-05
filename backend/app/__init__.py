from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from app.config import Config
from app.extensions import init_mongo

bcrypt = Bcrypt()
mail = Mail()
login_manager = LoginManager()
jwt = JWTManager()

# Disable redirect-based behavior (important for APIs)
login_manager.login_view = None
login_manager.login_message = None

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Disable strict slashes to prevent 308 redirects that break CORS preflight
    app.url_map.strict_slashes = False

    # Allow React to talk to Flask
    CORS(
        app,
        supports_credentials=True,
        resources={r"/*": {"origins": ["http://localhost:5173", "http://localhost:8080", "http://127.0.0.1:5173", "http://127.0.0.1:8080"]}}
    )
    # Init extensions
    init_mongo(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    jwt.init_app(app)

    # Register API blueprints
    # Register blueprints
    from app.auth.routes import auth_bp
    from app.users.routes import users_bp
    from app.events.routes import events_bp
    from app.expenses.routes import expenses_bp
    from app.dashboards.routes import bp as dashboards_bp
    from app.analytics.routes import analytics_bp
    from app.payments.routes import bp as payments_bp
    from app.wallets.routes import bp as wallets_bp
    from app.settlements.routes import bp as settlements_bp
    from app.notifications.routes import bp as notifications_bp
    
    app.register_blueprint(expenses_bp, url_prefix='/api/v1/expenses')
    app.register_blueprint(events_bp, url_prefix='/api/v1/events')
    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
    app.register_blueprint(users_bp, url_prefix='/api/v1/users')
    app.register_blueprint(payments_bp, url_prefix='/api/v1/payments')
    app.register_blueprint(dashboards_bp, url_prefix='/api/v1/dashboards')
    app.register_blueprint(analytics_bp, url_prefix='/api/v1/analytics')
    app.register_blueprint(wallets_bp, url_prefix='/api/v1/wallets')
    app.register_blueprint(settlements_bp, url_prefix='/api/v1/settlements')
    app.register_blueprint(notifications_bp, url_prefix='/api/v1/notifications')

    return app

from app.users.model import User

@login_manager.user_loader
def load_user(user_id):
    print(f"[USER_LOADER] Loading user with id: {user_id}")
    user_dict = User.find_by_id(user_id)
    print(f"[USER_LOADER] Found user_dict: {user_dict}")
    if user_dict:
        return User(user_dict)
    return None