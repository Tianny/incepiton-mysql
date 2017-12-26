import os

from flask_script import Manager, Shell
from flask_migrate import Migrate, MigrateCommand

from app import db
from app import create_app
from app.models import User


app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)
migrate = Migrate(app, db)


def make_shell_context():
    # return dict(app=app, db=db, User=User, Dbconfig=Dbconfig, Work=Work)
    return dict(app=app, db=db, User=User)


manager.add_command('shell', Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()
