from flask import render_template, url_for, redirect
from flask_login import current_user, login_required

from . import main


@main.route('/')
def index():
    return redirect(url_for('auth.login'))


@main.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'dev':
        return redirect(url_for('dev.dev_chart', days=7))
    else:
        return render_template('main/dashboard.html')
