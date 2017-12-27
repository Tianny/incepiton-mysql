from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, PasswordField
from wtforms.validators import DataRequired


class DbForm(FlaskForm):
    name = StringField(u'Name', validators=[DataRequired()])
    master_host = StringField(u'Master Address', validators=[DataRequired()])
    master_port = IntegerField(u'Master Port', validators=[DataRequired()])
    slave_host = StringField(u'Slave Address', validators=[DataRequired()])
    slave_port = IntegerField(u'Slave Port', validators=[DataRequired()])
    username = StringField(u'Username', validators=[DataRequired()])
    password = PasswordField(u'password', validators=[DataRequired()])


class UserForm(FlaskForm):
    name = StringField(u'Username', validators=[DataRequired()])
    password = PasswordField(u'Password', validators=[DataRequired()])
    role = StringField(u'Role', validators=[DataRequired()])
    email = StringField(u'Mail', validators=[DataRequired()])


class ModifyRoleForm(FlaskForm):
    role = StringField(u'Role', validators=[DataRequired()])


class UserDbForm(FlaskForm):
    db = IntegerField(u'Db', validators=[DataRequired()])
