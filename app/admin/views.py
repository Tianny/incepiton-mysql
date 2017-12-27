import base64
from datetime import datetime

from flask import render_template, redirect, url_for

from .. import admin_permission
from ..models import Dbconfig, User
from .form import DbForm, UserForm, ModifyRoleForm, UserDbForm
from . import admin


@admin.route('/db')
@admin_permission.require()
def db():
    dbconfigs = Dbconfig.query.all()
    return render_template('admin/db.html', dbconfigs=dbconfigs)


@admin.route('/db/create', methods=['GET', 'POST'])
@admin_permission.require()
def db_create():
    form = DbForm()
    if form.validate_on_submit():
        dbconfig = Dbconfig()
        dbconfig.name = form.name.data
        dbconfig.master_host = form.master_host.data
        dbconfig.master_port = form.master_port.data
        dbconfig.slave_host = form.slave_host.data
        dbconfig.slave_port = form.slave_port.data
        dbconfig.username = form.username.data
        dbconfig.password = base64.b64encode(form.password.data)
        db.session.add(dbconfig)
        db.session.commit()

        return redirect(url_for('.db'))

    return render_template('admin/db_create.html', form=form)


@admin.route('/db/update/<int:id>', methods=['GET', 'POST'])
@admin_permission.require()
def db_update(id):
    dbconfig = Dbconfig.query.get(id)
    form = DbForm()
    if form.validate_on_submit():
        dbconfig.name = form.name.data
        dbconfig.master_host = form.master_host.data
        dbconfig.master_port = form.master_port.data
        dbconfig.slave_host = form.slave_host.data
        dbconfig.slave_port = form.slave_port.data
        dbconfig.username = form.username.data
        dbconfig.password = base64.b64encode(form.password.data)
        dbconfig.update_time = datetime.now()
        db.session.add(dbconfig)
        db.session.commit()

        return redirect(url_for('.db'))

    return render_template('admin/db_update.html', form=form, dbconfig=dbconfig)


@admin.route('/db/delete/<int:id>')
@admin_permission.require()
def db_delete(id):
    dbconfig = Dbconfig.query.get(id)
    db.session.delete(dbconfig)
    db.session.commit()

    return redirect(url_for('.db'))


@admin.route('/user')
@admin_permission.require()
def user():
    users = User.query.filter(User.role != 'admin')
    return render_template('admin/user.html', users=users)


@admin.route('/user/create', methods=['GET', 'POST'])
@admin_permission.require()
def user_create():
    form = UserForm()
    if form.validate_on_submit():
        user = User()
        user.name = form.name.data
        user.hash_pass = user.set_password(form.password.data)
        user.role = form.role.data
        user.email = form.email.data
        db.session.add(user)
        db.session.commit()

        return redirect(url_for('.user'))

    return render_template('admin/user_create.html', form=form)


@admin.route('/user/update/<int:id>', methods=['GET', 'POST'])
@admin_permission.require()
def user_update(id):
    user = User.query.get(id)
    form = ModifyRoleForm()
    if form.validate_on_submit():
        user.role = form.role.data
        db.session.add(user)
        db.session.commit()

        return redirect(url_for('.user'))

    return render_template('admin/user_update.html', form=form, user=user)


@admin.route('/user/delete/<int:id>', methods=['GET', 'POST'])
@admin_permission.require()
def user_delete(id):
    user = User.query.get(id)
    db.session.delete(user)
    db.session.commit()

    return redirect(url_for('.user'))


@admin.route('/user/alloc/<int:id>', methods=['GET', 'POST'])
@admin_permission.require()
def user_alloc(id):
    user = User.query.get(id)
    user_dbconfigs = user.dbs
    all_dbconfigs = Dbconfig.query.all()

    for user_dbconfig in user_dbconfigs:
        if user_dbconfig in all_dbconfigs:
            all_dbconfigs.remove(user_dbconfig)

    form = UserDbForm()
    if form.validate_on_submit():
        dbconfig = Dbconfig.query.get(form.db.data)
        user.dbs.append(dbconfig)
        db.session.add(user)
        db.session.commit()

        return redirect(url_for('.user_alloc', id=id))

    return render_template(
        'admin/user_alloc.html',
        form=form,
        user=user,
        user_dbconfigs=user_dbconfigs,
        all_dbconfigs=all_dbconfigs
    )


@admin.route('/user/unbind/<int:user_id><int:db_id>')
@admin_permission.require()
def user_unbind(user_id, db_id):
    user = User.query.get(user_id)
    dbconfig = Dbconfig.query.get(db_id)
    user.dbs.remove(dbconfig)
    db.session.add(user)
    db.session.commit()

    return redirect(url_for('.user_db_alloc', id=user_id))
