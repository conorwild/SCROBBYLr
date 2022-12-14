from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_login import LoginManager
from sqlalchemy import event
from multiprocessing.managers import BaseManager

db = SQLAlchemy()
ma = Marshmallow()

def _fk_pragma_on_connect(dbapi_con, con_record):
    dbapi_con.execute('pragma foreign_keys=ON')

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object('config')
    app.config.from_pyfile('config.py')

    db.init_app(app)
    ma.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth_bp.login'
    login_manager.init_app(app)

    from . import models

    @login_manager.user_loader
    def load_user(user_id):
        return models.User.query.get(int(user_id))

    connection_manager = BaseManager(
        ('', app.config["CONNECTION_MGR_PORT"]),
        app.config["CONNECTION_MGR_SECRET"]
    )

    connection_manager.connect()
    app.connection_manager = connection_manager

    from .discogs.utils import register_discogs_functions
    register_discogs_functions(app)


    with app.app_context():
        db.create_all()
        event.listen(db.engine, 'connect', _fk_pragma_on_connect)

        from .auth.routes import auth_bp as auth_blueprint
        app.register_blueprint(auth_blueprint)

        from .home.routes import main_bp as main_blueprint
        app.register_blueprint(main_blueprint)

        from .discogs.routes import discogs_bp as discogs_blueprint
        app.register_blueprint(discogs_blueprint)

        return app