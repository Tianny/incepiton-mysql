from datetime import datetime, date, timedelta
import re
import json

import sqlparse
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user

from .. import db
from .. import dev_permission
from ..models import Dbapply, User, Dbconfig, Work
from .form import DbApplyForm, WorkForm, UpdateWorkForm
from ..inception import sql_auto_review
from ..tasks import send_mail
from . import dev


@dev.route('/dev/resource')
@login_required
@dev_permission.require(http_exception=403)
def dev_resource():
    """
    Show user's db instances.
    :return:
    """
    user = User.query.filter(User.name == current_user.name).first()
    resources = user.dbs

    return render_template('dev/resource.html', resources=resources, user=user)


@dev.route('/dev/resource/status')
@login_required
@dev_permission.require(http_exception=403)
def dev_resource_status():
    """
    Show user's application status
    :return:
    """
    resources = Dbapply.query.filter(Dbapply.dev_name == current_user.name)

    return render_template('dev/resource_status.html', resources=resources)


@dev.route('/dev/resource/cancel/<int:id>')
@login_required
@dev_permission.require(http_exception=403)
def dev_resource_cancel(id):
    """
    Dev users cancelled the application
    :param id:
    :return:
    """
    resource = Dbapply.query.get(id)
    resource.status = 2
    resource.finish_time = datetime.now()

    db.session.add(resource)
    db.session.commit()

    if current_app.config['MAIL_ON_OFF'] == 'ON':
        auditor = User.query.filter(User.name == resource.audit_name).first()
        mail_content = "<p>Proposer：" + resource.dev_name + "</p>" + "<p>Db instance's name：" + resource.db_name + \
                       "</p>" + "<p>Dev has cancelled the application.</p>"
        send_mail.delay('【inception_mysql】Db instance application cancelled', mail_content, auditor.email)

    return redirect(url_for('.dev_resource_status'))


@dev.route('/dev/resource/request', methods=['GET', 'POST'])
@login_required
@dev_permission.require(http_exception=403)
def dev_resource_request():
    """
    Apply for db instances.
    :return:
    """
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

        if current_app.config['MAIL_ON_OFF'] == 'ON':
            auditor = User.query.filter(User.name == resource.audit_name).first()
            mail_content = "<p>Proposer：" + resource.dev_name + "</p>" + "<p>Db instance's name：" + resource.db_name + \
                           "</p>" + "<p>New db instance request</p>"
            send_mail.delay('【inception_mysql】New db instance request', mail_content, auditor.email)

        return redirect(url_for('.dev_resource_status'))

    return render_template(
        'dev/resource_request.html',
        form=form,
        user=user,
        audits=audits,
        user_dbs=user_dbs,
        all_dbs=all_dbs
    )


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
    """
    Create work order.
    :return:
    """
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

        sql_content = sql_content.rstrip().replace("\n", " ")

        # Only Create and Alter can be used with table shard
        shard_create = re.search('\s*create\s+', sql_content, flags=re.IGNORECASE)
        shard_alter = re.search('\s*alter\s+', sql_content, flags=re.IGNORECASE)
        shard_judge = shard_create or shard_alter

        if shard != '0' and not shard_judge:
            flash('Only Create and Alter sql can be used when using table shard!')

            return redirect(url_for('.dev_work_create'))

        # split joint sql with shard numbers
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

                if current_app.config['MAIL_ON_OFF'] == 'ON':
                    auditor = User.query.filter(User.name == work.audit_name).first()
                    mail_content = "<p>Proposer：" + work.dev_name + "</p>" + "<p>Sql Content：" + work.sql_content + \
                                   "</p>" + "<p>A new work sheet.</p>"
                    send_mail.delay('【inception_mysql】New work sheet', mail_content, auditor.email)

                return redirect(url_for('.dev_work'))
            else:
                flash('The return of Inception is null. May be something wrong with the SQL sentence ')

                return redirect(url_for('.dev_work_create'))
        else:
            flash('SQL sentences does not ends with ; Please Check!')

            return redirect(url_for('.dev_work_create'))

    return render_template('dev/work_create.html', form=form, db_ins=db_ins, audits=audits)


@dev.route('/dev/work/check', methods=['POST'])
@dev_permission.require(http_exception=403)
def dev_work_check():
    """
    SQL check button triggers this func.
    :return:
    """
    data = request.form
    sql_content = data['sql_content']
    db_in_name = data['db_in']
    shard = data['shard']
    final_result = {'status': 0, 'msg': 'ok', 'data': []}

    if not sql_content or not db_in_name:
        final_result['status'] = 1
        final_result['msg'] = 'DB or SQL is null !'

        return json.dumps(final_result)

    sql_content = sql_content.rstrip().replace("\n", " ")

    if sql_content[-1] != ';':
        final_result['status'] = 2
        final_result['msg'] = 'SQL not end with ; Please check !'

        return json.dumps(final_result)

    # Only Create and Alter can be used with table shard
    shard_create = re.search('\s*create\s+', sql_content, flags=re.IGNORECASE)
    shard_alter = re.search('\s*alter\s+', sql_content, flags=re.IGNORECASE)
    shard_judge = shard_create or shard_alter

    if shard != '0' and not shard_judge:
        final_result['status'] = 4
        final_result['msg'] = 'Only Create and Alter sql can be used when using table shard !'

        return json.dumps(final_result)

    # split joint sql with shard numbers
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

    # Submit the final SQL to Inception
    result = sql_auto_review(sql_content, db_in_name)

    if result is None or len(result) == 0:
        final_result['status'] = 3
        final_result['msg'] = 'The return of Inception is null. May be something wrong with the SQL'

        return json.dumps(final_result)

    final_result['data'] = result

    return json.dumps(final_result)


@dev.route('/dev/work/modify/<int:id>', methods=['GET', 'POST'])
@login_required
@dev_permission.require(http_exception=403)
def dev_work_modify(id):
    """
    Modify dev's work order.
    :param id:
    :return:
    """
    work = Work.query.get(id)
    db_ins = current_user.dbs
    audits = User.query.filter(User.role == 'audit')
    form = UpdateWorkForm()

    if form.validate_on_submit():
        shard = form.shard.data
        db_name = form.db_ins.data

        if form.backup.data:
            is_backup = True
        else:
            is_backup = False

        sql_content = form.sql_content.data.rstrip().replace("\n", " ")

        # Only Create and Alter can be used with table shard
        shard_create = re.search('\s*create\s+', sql_content, flags=re.IGNORECASE)
        shard_alter = re.search('\s*alter\s+', sql_content, flags=re.IGNORECASE)
        shard_judge = shard_create or shard_alter

        if shard != '0' and not shard_judge:
            flash('Only Create and Alter sql can be used when using table shard !')

            return redirect(url_for('.dev_work_modify', id=id))

        # split joint sql with shard numbers
        if shard != '0' and shard_judge:
            split_sql = sqlparse.split(sql_content)
            format_table = re.sub(" +", " ", split_sql[1])
            sql_content = ''

            for count in range(int(shard)):
                format_table_list = format_table.split(' ')
                table_shard_name = '`' + format_table_list[2].strip('`') + '_' + str(count) + '`'
                format_table_list[2] = table_shard_name
                sql_content += ' '.join(format_table_list)

            sql_content = split_sql[0] + sql_content

        if sql_content[-1] == ';':
            work.shard = shard
            work.backup = is_backup
            work.db_name = db_name
            work.audit_name = form.audit.data

            result = sql_auto_review(sql_content, db_name)
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
                work.sql_content = sql_content

                db.session.add(work)
                db.session.commit()

                if current_app.config['MAIL_ON_OFF'] == 'ON':
                    auditor = User.query.filter(User.name == work.audit_name).first()
                    mail_content = "<p>Proposer：" + work.dev_name + "</p>" + "<p>Modified Sql Content：" + \
                                   work.sql_content + "</p>"
                    send_mail.delay('【inception_mysql】Modified work sheet', mail_content, auditor.email)

                return redirect(url_for('.dev_work'))
            else:
                flash('The return of Inception is null. May be something wrong with the SQL')

                return redirect(url_for('.dev_work_modify', id=id))
        else:
            flash('SQL sentences does not ends with ; Please Check!')

            return redirect(url_for('.dev_work_modify', id=id))

    return render_template('dev/work_modify.html', form=form, work=work, db_ins=db_ins, audits=audits)


@dev.route('/dev/work/cancel/<int:id>', methods=['GET', 'POST'])
@login_required
@dev_permission.require(http_exception=403)
def dev_work_cancel(id):
    """
    Cancel work order by dev self
    :param id:
    :return:
    """
    work = Work.query.get(id)
    work.status = 5
    work.finish_time = datetime.now()

    db.session.add(work)
    db.session.commit()

    if current_app.config['MAIL_ON_OFF'] == 'ON':
        auditor = User.query.filter(User.name == work.audit_name).first()
        mail_content = "<p>Proposer：" + work.dev_name + "</p>" + "<p>Sql Content：" + work.sql_content + \
                       "</p>" + "<p>Dev has cancelled the work sheet.</p>"
        send_mail.delay('【inception_mysql】Work sheet cancelled', mail_content, auditor.email)

    return redirect(url_for('.dev_work'))


@dev.route('/dev/work/detail/<int:id>')
@login_required
@dev_permission.require(http_exception=403)
def dev_work_detail(id):
    """
    Show worker order status detail.
    :param id:
    :return:
    """
    work = Work.query.get(id)

    if work.status == 0 or work.status == 4:
        list_content = json.loads(work.execute_result)
    else:
        list_content = json.loads(work.auto_review)

    for content in list_content:
        content[4] = content[4].split('\n')
        content[5] = content[5].split('\r\n')

    return render_template('dev/work_detail.html', work=work, list_content=list_content)


@dev.route('/dev/chart/<int:days>')
@dev_permission.require(http_exception=403)
def dev_chart(days=7):
    day_range = []
    today = date.today()
    day_range.append(str(today))

    for day in range(1, days):
        date_tmp = today - timedelta(days=day)
        day_range.append(str(date_tmp))
    day_range.sort()

    day_counts = []

    for i in range(len(day_range)):
        day_count = Work.query.filter(Work.dev_name == current_user.name,
                                      Work.create_time.like(day_range[i] + '%')).count()
        day_counts.append(day_count)

    days_ago = today - timedelta(days=days)
    works = Work.query.filter(Work.dev_name == current_user.name, Work.create_time >= days_ago).group_by(Work.status)
    work_status = {
        'Success': 0,
        'Pending': 0,
        'Check Failed': 0,
        'Executing': 0,
        'Error': 0,
        'Dev Cancelled': 0,
        'Audit Cancelled': 0,
        'Audit Rejected': 0
    }

    for work in works:
        if work.status == 0:
            work_status['Success'] += 1
        elif work.status == 1:
            work_status['Pending'] += 1
        elif work.status == 2:
            work_status['Check Failed'] += 1
        elif work.status == 3:
            work_status['Executing'] += 1
        elif work.status == 4:
            work_status['Error'] += 1
        elif work.status == 5:
            work_status['Dev Cancelled'] += 1
        elif work.status == 6:
            work_status['Audit Cancelled'] += 1
        elif work.status == 7:
            work_status['Audit Rejected'] += 1

    return render_template('dev/chart.html', day_range=day_range, day_counts=day_counts, work_status=work_status,
                           days=days)
