from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, TextAreaField
from wtforms.validators import DataRequired


class DbApplyForm(FlaskForm):
    db = StringField(u'DBName', validators=[DataRequired()])
    audit = StringField(u'Audit', validators=[DataRequired()])


class WorkForm(FlaskForm):
    name = StringField(u'WorkName')
    db_ins = StringField(u'DBName', validators=[DataRequired()])
    shard = StringField(u'Shard', validators=[DataRequired()])
    backup = BooleanField(u'backup')
    audit = StringField(u'Auditor', validators=[DataRequired()])
    sql_content = TextAreaField(u'SqlContent', validators=[DataRequired()])
