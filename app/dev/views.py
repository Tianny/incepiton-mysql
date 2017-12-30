from datetime import datetime

from flask import render_template, redirect, url_for, current_app
from flask_login import login_required, current_user

from .. import db
from .. import dev_permission
from ..models import Dbapply, User, Dbconfig
from .form import DbApplyForm
from . import dev


@dev.route('/dev/resource')
@login_required
@dev_permission.require(http_exception=403)
def dev_resource():
    user = User.query.filter(User.name == current_user.name).first()
    resources = user.dbs

    return render_template('dev/resource.html', resources=resources, user=user)


@dev.route('/dev/resource/status')
@login_required
@dev_permission.require(http_exception=403)
def dev_resource_status():
    resources = Dbapply.query.filter(Dbapply.dev_name == current_user.name)

    return render_template('dev/resource_status.html', resources=resources)


@dev.route('/dev/resource/cancel/<int:id>')
@login_required
@dev_permission.require(http_exception=403)
def dev_resource_cancel(id):
    resource = Dbapply.query.get(id)
    resource.status = 2
    resource.finish_time = datetime.now()
    db.session.add(resource)
    db.session.commit()

    return redirect(url_for('.dev_resource'))


@dev.route('/dev/resource/request', methods=['GET', 'POST'])
@login_required
@dev_permission.require(http_exception=403)
def dev_resource_request():
    audits = User.query.filter(User.role == 'audit')
    user = User.query.filter(User.name == current_user.name).first()
    user_dbs = current_user.dbs
    all_dbs = Dbconfig.query.all()

    for user_db in user_dbs:
        if user_db in all_dbs:
            all_dbs.remove(user_db)

    form = DbApplyForm()
    if form.validate_on_submit():
        resource = Dbapply()
        resource.dev_name = current_user.name
        resource.db_name = form.db.data
        resource.audit_name = form.audit.data
        resource.status = 1
        resource.create_time = datetime.now()

        db.session.add(resource)
        db.session.commit()

        return redirect(url_for('.dev_resource_status'))

    return render_template(
        'dev/resource_request.html',
        form=form,
        user=user,
        audits=audits,
        user_dbs=user_dbs,
        all_dbs=all_dbs
    )
