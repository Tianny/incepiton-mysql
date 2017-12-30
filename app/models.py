from datetime import datetime

from flask_login import UserMixin, AnonymousUserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from . import db
from . import login_manager

dbs = db.Table(
    'dbs',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('dbconfig_id', db.Integer, db.ForeignKey('dbconfig.id'))
)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    hash_pass = db.Column(db.String(200))
    email = db.Column(db.String(64))
    role = db.Column(db.String(64))
    dbs = db.relationship('Dbconfig', secondary=dbs, backref=db.backref('users', lazy='dynamic'))

    def set_password(self, password):
        self.hash_pass = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hash_pass, password)

    # Flask-login
    def get_id(self):
        return str(self.id)  # python3 use str, while python2 use unicode

    def __repr__(self):
        return "<User '{}'>".format(self.username)


# AnonymousUser
class AnonymousUser(AnonymousUserMixin):
    pass


login_manager.anonymous_user = AnonymousUser


# Flask-login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Dbconfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    master_host = db.Column(db.String(200), )
    master_port = db.Column(db.Integer, default=3306)
    slave_host = db.Column(db.String(200), )
    slave_port = db.Column(db.Integer, default=3306)
    username = db.Column(db.String(64))
    password = db.Column(db.String(100))
    create_time = db.Column(db.DateTime, default=datetime.now())
    update_time = db.Column(db.DateTime, default=datetime.now())


class Dbapply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dev_name = db.Column(db.String(64))
    db_name = db.Column(db.String(64))
    audit_name = db.Column(db.String(64))
    status = db.Column(db.Integer)
    create_time = db.Column(db.DateTime, default=datetime.now())
    finish_time = db.Column(db.DateTime)


