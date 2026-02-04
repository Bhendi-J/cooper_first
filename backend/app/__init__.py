from flask import Flask
from app.config import Config
from app.extensions import mongo, jwt, cors

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    mongo.init_app(app)
    jwt.init_app(app)
    cors.init_app(app)
    
    # Register blueprints
    from app.auth.routes import auth_bp
    from app.users.routes import users_bp
    from app.events.routes import events_bp
    from app.wallets.routes import wallets_bp
    from app.expenses.routes import expenses_bp
    from app.payments.routes import payments_bp
    from app.settlements.routes import settlements_bp
    from app.dashboards.routes import dashboards_bp
    from app.ai.routes import ai_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
    app.register_blueprint(users_bp, url_prefix='/api/v1/users')
    app.register_blueprint(events_bp, url_prefix='/api/v1/events')
    app.register_blueprint(wallets_bp, url_prefix='/api/v1/wallets')
    app.register_blueprint(expenses_bp, url_prefix='/api/v1/expenses')
    app.register_blueprint(payments_bp, url_prefix='/api/v1/payments')
    app.register_blueprint(settlements_bp, url_prefix='/api/v1/settlements')
    app.register_blueprint(dashboards_bp, url_prefix='/api/v1/dashboards')
    app.register_blueprint(ai_bp, url_prefix='/api/v1/ai')
    
    return app