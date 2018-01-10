from flask import current_app
from flask_mail import Message

from . import celery, mail
from .inception import execute_final


@celery.task()
def execute_task(id):
    app = current_app._get_current_object()

    return execute_final(app, id)


@celery.task()
def send_mail(subject, body, receiver):
    msg = Message(subject, recipients=[receiver])
    msg.html = body
    mail.send(msg)
