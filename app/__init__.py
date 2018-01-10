from datetime import timedelta

from flask import Flask
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_simpleldap import LDAP
from flask_principal import Principal, identity_loaded, RoleNeed, UserNeed, Permission
from flask_celery import Celery

from config import config

mail = Mail()
db = SQLAlchemy()

# flask_login manager
login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'auth.login'
login_manager.remember_cookie_duration = timedelta(minutes=5)

# ldap
ldap = LDAP()

# flask_principal
principals = Principal()
dev_permission = Permission(RoleNeed('dev'))
audit_permission = Permission(RoleNeed('audit'))
admin_permission = Permission(RoleNeed('admin'))

# celery
celery = Celery()


def create_app(config_name):
    """
    application initialization
    :param config_name:
    :return:
    """

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    mail.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    ldap.init_app(app)

    # flask_principal
    principals.init_app(app)

    @identity_loaded.connect_via(app)
    def on_identity_loaded(sender, identity):
        identity.user = current_user

        if hasattr(current_user, 'id'):
            identity.provides.add(UserNeed(current_user.id))

        if hasattr(current_user, 'role'):
            identity.provides.add(RoleNeed(current_user.role))

    # celery
    celery.init_app(app)

    # register blue_print
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint)

    from .audit import audit as audit_blueprint
    app.register_blueprint(audit_blueprint)

    from .dev import dev as dev_blueprint
    app.register_blueprint(dev_blueprint)

    return app
