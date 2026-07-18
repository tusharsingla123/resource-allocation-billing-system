from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from datetime import timedelta
from sqlalchemy import event
from sqlalchemy.engine import Engine

# Initialize extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
migrate = Migrate()
login_manager = LoginManager()

def create_app(config_object='app.config.Config'):
    """Application factory pattern"""
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config.from_object(config_object)
    
    # Initialize extensions with app
    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.session_protection = 'strong'
    app.permanent_session_lifetime = timedelta(minutes=10)
    
    # Register blueprints
    from app.routes import auth, vessels, ports, config, statistics, notifications
    app.register_blueprint(auth.bp)
    app.register_blueprint(vessels.bp)
    app.register_blueprint(ports.bp)
    app.register_blueprint(config.bp)
    app.register_blueprint(statistics.bp)
    app.register_blueprint(notifications.bp)
    
    # Register template filters
    from app.utils.helpers import format_date, currency_format, currency_format_new
    app.jinja_env.filters['format_date'] = format_date
    app.jinja_env.filters['currency'] = currency_format
    app.jinja_env.filters['currency_new'] = currency_format_new
    
    # Register context processor
    from app.routes.notifications import inject_due_ports
    app.context_processor(inject_due_ports)
    
    # Register after_request handler
    from app.utils.decorators import add_header
    app.after_request(add_header)
    
    # Enable SQLite foreign keys
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    # Register user loader
    from app.models import User, Admin
    @login_manager.user_loader
    def load_user(user_id):
        user = User.query.get(int(user_id))
        if user:
            return user
        admin = Admin.query.get(int(user_id))
        if admin:
            return admin
        return None
    
    return app
