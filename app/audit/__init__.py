from flask import Blueprint

audit = Blueprint('audit', __name__)

from . import views