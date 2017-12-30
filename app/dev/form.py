from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired


class DbApplyForm(FlaskForm):
    db = StringField(u'DBName', validators=[DataRequired()])
    audit = StringField(u'Audit', validators=[DataRequired()])
