from datetime import datetime
import json

from flask import render_template, url_for, redirect
from flask_login import login_required, current_user

from .. import db
from .. import audit_permission
from ..models import Dbapply, User, Dbconfig, Work
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


@audit.route('/audit/work/pending')
@login_required
@audit_permission.require(http_exception=403)
def audit_work_pending():
    works = Work.query.filter(Work.audit_name == current_user.name, Work.status == 1, Work.timer == None)

    return render_template('audit/work_pending.html', works=works)


@audit.route('/audit/work/dealt')
@login_required
@audit_permission.require(http_exception=403)
def audit_work_dealt():
    works = Work.query.filter(Work.audit_name == current_user.name, Work.status != 1)

    return render_template('audit/work_dealt.html', works=works)


@audit.route('/audit/work/detail/<int:id>')
@login_required
@audit_permission.require(http_exception=403)
def audit_work_detail(id):
    work = Work.query.get(id)
    backtimer = 0

    if work.timer is not None:
        backtimer = 1

    if work.stats == 0 or work.status == 4:
        list_content = json.loads(work.execute_result)
    else:
        list_content = json.loads(work.auto_review)

    for content in list_content:
        content[4] = content[4].split('\n')
        content[5] = content[5].split('\r\n')

    return render_template('audit/work_detail.html', work=work, list_content=list_content, backtimer=backtimer)


@audit.route('/audit/work/cancel/<int:id>')
@login_required
@audit_permission.require(http_exception=403)
def audit_work_cancel(id):
    work = Work.query.get(id)
    work.status = 6
    work.finish_time = datetime.now()
    db.session.add(work)
    db.session.commit()

    return redirect(url_for('.audit_work_dealt'))


@audit.route('/audit/work/reject/<int:id>')
@login_required
@audit_permission.require(http_exception=403)
def audit_work_reject(id):
    work = Work.query.get(id)
    work.status = 7
    work.finish_time = datetime.now()
    db.session.add(work)
    db.session.commit()

    return redirect(url_for('.audit_work_dealt'))