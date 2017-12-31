from datetime import datetime
import re
import json

import sqlparse
from flask import render_template, redirect, url_for, current_app, flash
from flask_login import login_required, current_user

from .. import db
from .. import dev_permission
from ..models import Dbapply, User, Dbconfig, Work
from .form import DbApplyForm, WorkForm
from ..inception import sql_auto_review
from . import dev

"""
DB Instances Apply
"""


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


"""
Dev Work Sheets
"""


@dev.route('/dev/work')
@login_required
@dev_permission.require(http_exception=403)
def dev_work():
    works = Work.query.filter(Work.dev_name == current_user.name)

    return render_template('dev/work.html', works=works)


@dev.route('/dev/work/create', methods=['GET', 'POST'])
@login_required
@dev_permission.require(http_exception=403)
def dev_work_create():
    db_ins = current_user.dbs
    audits = User.query.filter(User.role == 'audit')
    form = WorkForm()
    if form.validate_on_submit():
        sql_content = form.sql_content.data
        db_ins = form.db_ins.data
        shard = form.shard.data
        if form.backup.data:
            is_backup = True
        else:
            is_backup = False

        sql_content = sql_content.rstrip().encode('utf-8').replace("\n", " ")

        shard_create = re.search('\s*create\s+', sql_content, flags=re.IGNORECASE)
        shard_alter = re.search('\s*alter\s+', sql_content, flags=re.IGNORECASE)
        shard_judge = shard_create or shard_alter

        if shard != '0' and not shard_judge:
            flash(u'Only Create and Alter sql can be used when using table shard!')
        if shard != '0' and shard_judge:
            split_sql = sqlparse.split(sql_content)
            format_table = re.sub(" +", " ", split_sql[1])
            sql_content = ''
            for count in range(int(shard)):
                format_table_list = format_table.split(' ')
                shard_name = '`' + str(format_table_list[2].strip('`')) + '_' + str(count) + '`'
                format_table_list[2] = shard_name
                sql_content += ' '.join(format_table_list)
            sql_content = split_sql[0] + sql_content

        if sql_content[-1] == ';':
            work = Work()
            work.name = form.name.data
            work.db_name = form.db_ins.data
            work.shard = form.shard.data
            work.backup = is_backup
            work.dev_name = current_user.name
            work.audit_name = form.audit.data
            work.sql_content = sql_content

            result = sql_auto_review(sql_content, db_ins)
            if result or len(result) != 0:
                json_result = json.dumps(result)
                work.status = 1
                for row in result:
                    if row[2] == 2:
                        work.status = 2
                        break
                    elif re.match(r"\w*comments\w*", row[4]):
                        work.status = 2
                        break
                work.auto_review = json_result
                work.create_time = datetime.now()

                db.session.add(work)
                db.session.commit()

                return redirect(url_for('.dev_work'))
            else:
                flash(u'The return of Inception is null. May be something wrong with the SQL sentence ')
        else:
            flash(u'SQL sentences does not ends with ; punctuation, Please Check!')

    return render_template('dev/dev_work_create.html', form=form, db_ins=db_ins, audits=audits)
