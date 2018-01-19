from werkzeug.security import generate_password_hash
from flask import render_template, current_app, g, flash, url_for, redirect
from flask_login import current_user, login_user, logout_user, login_required
from flask_principal import Identity, AnonymousIdentity, identity_changed

from .. import db, ldap
from . import auth
from .form import LoginForm, RegisterForm
from ..models import User


@auth.before_app_request
def before_request():
    g.user = current_user


@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter(User.name == form.username.data).first()

        if current_app.config['LDAP_ON_OFF'] == 'ON':

            # Admin account separate from ldap
            if user is not None and user.name == 'admin':
                if user.check_password(form.password.data):
                    login_user(user, form.remember_me.data)
                    identity_changed.send(current_app._get_current_object(), identity=Identity(user.id))

                    return redirect(url_for('main.dashboard'))
                else:
                    flash('Invalid password', category='warning')

                return redirect(url_for('.login'))

            if user is not None:
                validator = ldap.bind_user(form.username.data, form.password.data)

                if validator is not None:

                    # Ldap authentication success then check the password stored in db
                    if user.check_password(form.password.data):
                        login_user(user, form.remember_me.data)
                        identity_changed.send(current_app._get_current_object(), identity=Identity(user.id))

                        return redirect(url_for('main.dashboard'))
                    else:

                        # Ldap authentication success and update the correct ldap password into db
                        user.hash_pass = user.set_password(form.password.data)
                        db.session.add(user)
                        db.session.commit()

                        login_user(user, form.remember_me.data)
                        identity_changed.send(current_app._get_current_object(), identity=Identity(user.id))

                        return redirect(url_for('main.dashboard'))
                else:
                    flash('Ldap Authentication Fail', category='warning')
            else:
                validator = ldap.bind_user(form.username.data, form.password.data)

                # Ldap authentication success but user does not exists in db, then create it in db.
                if validator is not None:
                    user = User()
                    user.name = form.username.data
                    user.hash_pass = generate_password_hash(form.password.data)
                    user.role = 'dev'
                    user.email = form.username.data + '@example.com'
                    db.session.add(user)
                    db.session.commit()

                    login_user(user, form.remember_me.data)
                    identity_changed.send(current_app._get_current_object(), identity=Identity(user.id))

                    return redirect(url_for('main.dashboard'))
                else:
                    flash('Ldap Authentication Fail', category='warning')
        else:
            if user is not None and user.check_password(form.password.data):
                login_user(user, form.remember_me.data)
                identity_changed.send(current_app._get_current_object(), identity=Identity(user.id))

                return redirect(url_for('main.dashboard'))
            else:
                flash('Invalid username or password', category='warning')

    return render_template("auth/login.html", form=form, current_app=current_app)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    identity_changed.send(current_app._get_current_object(), identity=AnonymousIdentity())

    return redirect(url_for('.login'))


@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        user = User()
        user.name = form.username.data
        user.hash_pass = generate_password_hash(form.password.data)
        user.email = form.email.data

        # Register user's role is dev, by default.
        user.role = 'dev'

        db.session.add(user)
        db.session.commit()

        flash('You have registered successfully. Please login! ', category='success')

        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)
