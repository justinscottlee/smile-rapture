from flask import Flask
from flask_socketio import SocketIO
from flask_htmx import HTMX

from config import Config

socketio = SocketIO()
htmx = HTMX()


def create_app(config_class=Config):
    app = Flask(__name__, template_folder='templates/', static_folder='static/')
    app.config.from_object(config_class)

    from app.services.auth import bcrypt
    bcrypt.init_app(app)

    socketio.init_app(app)
    htmx.init_app(app)

    from app.routes.api import bp as api_bp
    app.register_blueprint(api_bp)

    from app.routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from app.routes.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.routes.admin import bp as admin_bp
    app.register_blueprint(admin_bp)

    from app.context_processor import utility_processor, inject_current_app
    app.context_processor(utility_processor)
    app.context_processor(inject_current_app)

    from app.services.auth import check_and_create_admin
    check_and_create_admin()

    # SocketIO imports
    from app.routes.api.node import update_node_type

    return app


from app import models
