from flask_login import UserMixin, AnonymousUserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from . import db
from . import login_manager


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    hash_pass = db.Column(db.String(200))
    email = db.Column(db.String(64))
    role = db.Column(db.String(120))

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
