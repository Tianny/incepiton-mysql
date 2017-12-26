from flask import render_template, current_app, request, flash, make_response, send_file, url_for, jsonify, redirect
from flask_login import current_user, login_required

from . import main


@main.route('/')
def index():
    return redirect(url_for('auth.login'))


@main.route('/dashboard')
@login_required
def dashboard():
    return render_template('main/dashboard.html')
