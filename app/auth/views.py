from flask import render_template, current_app, g, flash, url_for, redirect
from flask_login import current_user, login_user, logout_user, login_required
from flask_principal import Identity, AnonymousIdentity, identity_changed

from .. import db, ldap
from . import auth
from .form import LoginForm
from ..models import User


@auth.before_app_request
def before_request():
    g.user = current_user


@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter(User.name == form.username.data).first()
        if user is not None and user.name == 'admin':
            if user.check_password(form.password.data):
                login_user(user, form.remember_me.data)
                identity_changed.send(current_app._get_current_object(), identity=Identity(user.id))
                return redirect(url_for('main.dashboard'))
            else:
                flash(u'Invalid password')
                return redirect(url_for('.login'))

        if user is not None:
            validator = ldap.bind_user(form.username.data, form.password.data)
            if validator is not None:
                if user.check_password(form.password.data):
                    login_user(user, form.remember_me.data)
                    identity_changed.send(current_app._get_current_object(), identity=Identity(user.id))
                    return redirect(url_for('main.dashboard'))
                else:
                    user.hash_pass = user.set_password(form.password.data)
                    db.session.add(user)
                    db.session.commit()
                    login_user(user, form.remember_me.data)
                    identity_changed.send(current_app._get_current_object(), identity=Identity(user.id))
                    return redirect(url_for('main.dashboard'))
            else:
                flash(u'Ldap Authentication Fail')
        else:
            validator = ldap.bind_user(form.username.data, form.password.data)
            if validator is not None:
                user = User()
                user.name = form.username.data
                user.hash_pass = user.set_password(form.password.data)
                user.role = 'dev'
                user.email = form.username.data + '@in66.com'
                db.session.add(user)
                db.session.commit()
                login_user(user, form.remember_me.data)
                identity_changed.send(current_app._get_current_object(), identity=Identity(user.id))
                return redirect(url_for('main.dashboard'))
            else:
                flash(u'Ldap Authentication Fail')

    return render_template("auth/login.html", form=form)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    identity_changed.send(current_app._get_current_object(), identity=AnonymousIdentity())

    return redirect(url_for('.login'))
