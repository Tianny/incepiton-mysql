import os

from werkzeug.security import generate_password_hash
from flask_script import Manager, Shell, Command, Option
from flask_migrate import Migrate, MigrateCommand

from app import db
from app import create_app
from app.models import User

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)
migrate = Migrate(app, db)


class CreateUser(Command):
    option_list = (
        Option('--name', '-n', dest='name'),
        Option('--password', '-p', dest='password'),
        Option('--email', '-e', dest='email')
    )

    def run(self, name, password, email):
        user = User()
        user.name = name
        user.hash_pass = generate_password_hash(password)
        user.email = email

        db.session.add(user)
        db.session.commit()


def make_shell_context():
    return dict(app=app, db=db, User=User)


manager.add_command('shell', Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)
manager.add_command('create_user', CreateUser())

if __name__ == '__main__':
    manager.run()
