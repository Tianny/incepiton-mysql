from flask import current_app

from . import celery
from .inception import execute_final


@celery.task()
def log(msg):
    return msg


@celery.task()
def execute_task(id):
    app = current_app._get_current_object()

    return execute_final(app, id)
