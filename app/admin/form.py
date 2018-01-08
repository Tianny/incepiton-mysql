from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, PasswordField
from wtforms.validators import DataRequired


class DbForm(FlaskForm):
    """
    Definition for applying for db instance.
    """

    name = StringField('Name', validators=[DataRequired()])
    master_host = StringField('Master Address', validators=[DataRequired()])
    master_port = IntegerField('Master Port', validators=[DataRequired()])
    slave_host = StringField('Slave Address', validators=[DataRequired()])
    slave_port = IntegerField('Slave Port', validators=[DataRequired()])

    # username  used by Inception
    username = StringField('Username', validators=[DataRequired()])

    # password used by Inception
    password = PasswordField('password', validators=[DataRequired()])


class UserForm(FlaskForm):
    name = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    role = StringField('Role', validators=[DataRequired()])
    email = StringField('Mail', validators=[DataRequired()])


class ModifyRoleForm(FlaskForm):
    role = StringField('Role', validators=[DataRequired()])


class UserDbForm(FlaskForm):
    db = IntegerField('Db', validators=[DataRequired()])
