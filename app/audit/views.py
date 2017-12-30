from datetime import datetime

from flask import render_template, url_for, redirect
from flask_login import login_required, current_user

from .. import db
from .. import audit_permission
from ..models import Dbapply, User, Dbconfig
from . import audit


@audit.route('/audit/resource/dealt')
@login_required
@audit_permission.require(http_exception=403)
def audit_resource_dealt():
    resources = Dbapply.query.filter(Dbapply.audit_name == current_user.name, Dbapply.status != 1)

    return render_template('audit/resource_dealt.html', resources=resources)


@audit.route('/audit/resource/pending')
@login_required
@audit_permission.require(http_exception=403)
def audit_resource_pending():
    resources = Dbapply.query.filter(Dbapply.audit_name == current_user.name, Dbapply.status == 1)

    return render_template('audit/resource_pending.html', resources=resources)


@audit.route('/audit/resource/alloc/<int:id>')
@login_required
@audit_permission.require(http_exception=403)
def audit_resource_alloc(id):
    resource = Dbapply.query.get(id)
    user = User.query.filter(User.name == resource.dev_name).first()
    db_config = Dbconfig.query.filter(Dbconfig.name == resource.db_name).first()
    user.dbs.append(db_config)
    resource.finish_time = datetime.now()
    resource.status = 0

    db.session.add(resource)
    db.session.commit()

    resources = Dbapply.query.filter(Dbapply.audit_name == current_user.name, Dbapply.status == 1)

    return redirect(url_for('.audit_resource_pending', resources=resources))


@audit.route('/audit/resource/cancel/<int:id>')
@login_required
@audit_permission.require(http_exception=403)
def audit_resource_cancel(id):
    resource = Dbapply.query.get(id)
    resource.status = 3
    resource.finish_time = datetime.now()
    db.session.add(resource)
    db.session.commit()

    return redirect(url_for('.audit_resource_dealt'))