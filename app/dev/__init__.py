from flask import Blueprint

dev = Blueprint('dev', __name__)

from . import views
