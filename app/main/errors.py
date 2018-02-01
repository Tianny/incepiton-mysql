from flask import render_template

from . import main


@main.app_errorhandler(404)
def page_not_found(e):
    return render_template('main/404.html'), 404


@main.app_errorhandler(403)
def privilege_error(e):
    return render_template('main/403.html'), 403


@main.app_errorhandler(500)
def internal_server_error(e):
    return render_template('main/500.html'), 500
