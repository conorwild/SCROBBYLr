from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_login import LoginManager
from sqlalchemy import event
from celery import Celery
from config import Config

from .classes import CustomJSONDecoder, CustomJSONEncoder
import os


db = SQLAlchemy()
ma = Marshmallow()
celery = Celery(__name__,
    broker=Config.CELERY_BROKER_URL,
    result_backend=Config.CELERY_RESULT_BACKEND
)

def _fk_pragma_on_connect(dbapi_con, con_record):
    dbapi_con.execute('pragma foreign_keys=ON')

def create_app():
    app = Flask(__name__)

    CONFIG_TYPE = os.getenv('CONFIG_TYPE', default='config.DevelopmentConfig')
    app.config.from_object(CONFIG_TYPE)

    app.json_encoder = CustomJSONEncoder
    app.json_decoder = CustomJSONDecoder

    db.init_app(app)
    ma.init_app(app)
    
    celery.conf.update(app.config)

    login_manager = LoginManager()
    login_manager.login_view = 'auth_bp.login'
    login_manager.init_app(app)

    from . import models

    @login_manager.user_loader
    def load_user(user_id):
        return models.User.query.get(int(user_id))

    with app.app_context():
        db.create_all()
        event.listen(db.engine, 'connect', _fk_pragma_on_connect)

        from .auth import auth_bp as auth_blueprint
        app.register_blueprint(auth_blueprint)

        from .main import main_bp as main_blueprint
        app.register_blueprint(main_blueprint)

        from .discogs.routes import discogs_bp as discogs_blueprint
        app.register_blueprint(discogs_blueprint)

        register_error_handlers(app)

        return app

def register_error_handlers(app):

    # 400 - Bad Request
    @app.errorhandler(400)
    def bad_request(e):
        return render_template('400.html'), 400

    # 403 - Forbidden
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('403.html'), 403

    # 404 - Page Not Found
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    # 405 - Method Not Allowed
    @app.errorhandler(405)
    def method_not_allowed(e):
        return render_template('405.html'), 405

    # 500 - Internal Server Error
    @app.errorhandler(500)
    def server_error(e):
        return render_template('500.html'), 500