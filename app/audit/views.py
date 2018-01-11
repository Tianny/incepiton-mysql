from datetime import datetime
from datetime import timedelta
import json
import os

from flask import render_template, url_for, redirect, request, jsonify, flash, make_response, send_file, current_app
from flask_login import login_required, current_user

from .. import db, celery
from .. import audit_permission
from ..models import Dbapply, User, Dbconfig, Work
from ..inception import sql_auto_review, get_osc, stop_osc, get_sql_roll
from ..tasks import execute_task, send_mail
from . import audit

# Dictionary cache used for store SQL and corresponding SHA1
# Format: {work_flow_id1:{SQL_id1:sqlSHA1 value1, SQL_id2:sqlSHA1 value2}}
sql_sha1_cache = {}


@audit.route('/audit/resource/dealt')
@login_required
@audit_permission.require(http_exception=403)
def audit_resource_dealt():
    """
    Application from dev for db instances have been dealt.
    :return:
    """
    resources = Dbapply.query.filter(Dbapply.audit_name == current_user.name, Dbapply.status != 1)

    return render_template('audit/resource_dealt.html', resources=resources)


@audit.route('/audit/resource/pending')
@login_required
@audit_permission.require(http_exception=403)
def audit_resource_pending():
    """
    Application from dev for db instances will to be handled.
    :return:
    """
    resources = Dbapply.query.filter(Dbapply.audit_name == current_user.name, Dbapply.status == 1)

    return render_template('audit/resource_pending.html', resources=resources)


@audit.route('/audit/resource/alloc/<int:id>', methods=['POST', 'GET'])
@login_required
@audit_permission.require(http_exception=403)
def audit_resource_alloc(id):
    """
    Alloc db instances to dev.
    :param id:
    :return:
    """
    resource = Dbapply.query.get(id)
    user = User.query.filter(User.name == resource.dev_name).first()
    db_config = Dbconfig.query.filter(Dbconfig.name == resource.db_name).first()
    user.dbs.append(db_config)
    resource.finish_time = datetime.now()
    resource.status = 0

    db.session.add(resource)
    db.session.commit()

    if current_app.config['MAIL_ON_OFF'] == 'ON':
        dev = User.query.filter(User.name == resource.dev_name).first()
        mail_content = "<p>Proposer：" + resource.dev_name + "</p>" + "<p>Db instance's name：" + resource.db_name + \
                       "</p>" + "<p>Your db instance request has been passed.</p>"
        send_mail.delay('【inception_mysql】Db instance request passed', mail_content, dev.email)

    return redirect(url_for('.audit_resource_pending'))


@audit.route('/audit/resource/cancel/<int:id>')
@login_required
@audit_permission.require(http_exception=403)
def audit_resource_cancel(id):
    """
    Cancelled the application from dev.
    :param id:
    :return:
    """
    resource = Dbapply.query.get(id)
    resource.status = 3
    resource.finish_time = datetime.now()

    db.session.add(resource)
    db.session.commit()

    if current_app.config['MAIL_ON_OFF'] == 'ON':
        dev = User.query.filter(User.name == resource.dev_name).first()
        mail_content = "<p>Proposer：" + resource.dev_name + "</p>" + "<p>Db instance's name：" + resource.db_name + \
                       "</p>" + "<p>Your db instance request is disagreed.</p>"
        send_mail.delay('【inception_mysql】Db instance request failure', mail_content, dev.email)

    return redirect(url_for('.audit_resource_dealt'))


@audit.route('/audit/work/pending')
@login_required
@audit_permission.require(http_exception=403)
def audit_work_pending():
    """
    Work orders to be handled, exclude timer.
    :return:
    """
    works = Work.query.filter(Work.audit_name == current_user.name, Work.status == 1, Work.timer == None)

    return render_template('audit/work_pending.html', works=works)


@audit.route('/audit/work/dealt')
@login_required
@audit_permission.require(http_exception=403)
def audit_work_dealt():
    """
    Work orders has been handled.
    :return:
    """
    works = Work.query.filter(Work.audit_name == current_user.name, Work.status != 1)

    return render_template('audit/work_dealt.html', works=works)


@audit.route('/audit/work/detail/<int:id>')
@login_required
@audit_permission.require(http_exception=403)
def audit_work_detail(id):
    """
    Show more information about the work order and operations
    :param id:
    :return:
    """
    work = Work.query.get(id)
    backtimer = 0

    if work.timer is not None:
        backtimer = 1

    if work.status == 0 or work.status == 4:
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
    """
    Cancel the work order by auditor.
    :param id:
    :return:
    """
    work = Work.query.get(id)
    work.status = 6
    work.finish_time = datetime.now()
    db.session.add(work)
    db.session.commit()

    if current_app.config['MAIL_ON_OFF'] == 'ON':
        dev = User.query.filter(User.name == work.dev_name).first()
        mail_content = "<p>Work Sheet：" + work.name + " is cancelled by auditor. Please contact with your auditor.</p>"
        send_mail.delay('【inception_mysql】Work Sheet Cancelled', mail_content, dev.email)

    return redirect(url_for('.audit_work_dealt'))


@audit.route('/audit/work/reject/<int:id>')
@login_required
@audit_permission.require(http_exception=403)
def audit_work_reject(id):
    """
    Reject the work order by auditor.
    :param id:
    :return:
    """
    work = Work.query.get(id)
    work.status = 7
    work.finish_time = datetime.now()
    db.session.add(work)
    db.session.commit()

    if current_app.config['MAIL_ON_OFF'] == 'ON':
        dev = User.query.filter(User.name == work.dev_name).first()
        mail_content = "<p>Work Sheet：" + work.name + " is rejected by auditor. Please modify it.</p>"
        send_mail.delay('【inception_mysql】Work Sheet Rejected', mail_content, dev.email)

    return redirect(url_for('.audit_work_dealt'))


@audit.route('/audit/work/execute', methods=['POST'])
@audit_permission.require()
def audit_work_execute():
    data = request.form
    id = int(data['workflowid'])
    work = Work.query.filter(Work.id == id).first()

    if work.timer is None:
        work.task_id = str(id)
        work.status = 3
        work.man_review_time = datetime.now()

        # 执行之前重新split并check一遍，更新SHA1缓存；因为如果在执行中，其他进程去做这一步操作的话，会导致inception core dump挂掉
        split_review_result = sql_auto_review(work.sql_content, work.db_name, is_split='yes')
        work.auto_review = json.dumps(split_review_result)

        db.session.add(work)
        db.session.commit()

        async_result = execute_task.apply_async(args=[id], task_id=str(id))

        if current_app.config['MAIL_ON_OFF'] == 'ON':
            dev = User.query.filter(User.name == work.dev_name).first()
            mail_content = "<p>Work Sheet：" + work.name + " is executing. </p>" + "<p>Please view it</p>"
            send_mail.delay('【inception_mysql】Work Sheet Inform', mail_content, dev.email)

    return jsonify({}), 202, {'Location': url_for('.audit_work_detail', id=id)}


@audit.route('/audit/timer/work/<int:id>', methods=['GET', 'POST'])
@audit_permission.require(http_exception=403)
def audit_work_timer(id):
    """
    Set timer for work order.
    :param id:
    :return:
    """
    work = Work.query.get(id)
    if request.method == "POST":
        data = request.form
        timer = datetime.strptime(data["dt"], "%Y-%m-%d %H:%M")
        now = datetime.now()

        # Fix the celery 4.0.1 timezone bug.
        # See detail here https://github.com/celery/celery/pull/4173/
        eta = timer - timedelta(hours=8)

        if timer > now:
            sig = execute_task.signature((id,), eta=eta)
            if work.timer is None:
                async_result = sig.apply_async()
                work.task_id = async_result.id
                work.timer = timer

                db.session.add(work)
                db.session.commit()
            else:
                celery.control.revoke(work.task_id, terminate=True)
                async_result = sig.apply_async()
                work.task_id = async_result.id
                work.timer = timer

                db.session.add(work)
                db.session.commit()
        else:
            flash('Timer must later then now')

    return render_template('audit/work_timer.html', work=work)


@audit.route('/audit/timer/cancel/<int:id>')
@audit_permission.require(http_exception=403)
def audit_work_timer_cancel(id):
    """
    Cancel timer set.
    :param id:
    :return:
    """
    work = Work.query.get(id)
    celery.control.revoke(work.task_id, terminate=True)
    work.task_id = None
    work.timer = None

    db.session.add(work)
    db.session.commit()

    return redirect(url_for('.audit_work_timer', id=id))


@audit.route('/audit/timer/view')
@audit_permission.require(http_exception=403)
def audit_work_timer_view():
    """
    Show work orders which have timer.
    :return:
    """
    works = Work.query.filter(Work.timer != None).all()

    return render_template('audit/work_timer_view.html', works=works)


@audit.route('/audit/timer/detail/<int:id>')
@audit_permission.require(http_exception=403)
def audit_work_timer_detail(id):
    work = Work.query.get(id)

    return render_template('audit/work_timer_detail.html', work=work)


@audit.route('/timer_celery_status', methods=['POST'])
@audit_permission.require(http_exception=403)
def timer_celery_status():
    """
    Get status from celery.
    :return:
    """
    work_flow_tid = request.form['workflowtid']

    if work_flow_tid == '' or work_flow_tid is None:
        context = {'status': -1, 'msg': 'work_flow_tid is null', 'data': ''}

        return jsonify(context)

    task = celery.AsyncResult(work_flow_tid)

    if task.state == 'PENDING':
        context = {'status': 1, 'msg': 'Wait', 'data': ''}
        return jsonify(context)

    elif task.state == 'STARTED':
        context = {'status': 2, 'msg': 'Executing', 'data': ''}
        return jsonify(context)

    elif task.state == 'RETRY':
        context = {'status': 3, 'msg': 'Retrying', 'data': ''}
        return jsonify(context)

    elif task.state == 'SUCCESS':
        context = {'status': 0, 'msg': 'Success', 'data': ''}
        return jsonify(context)


def get_sql_sha1(work_flow_id):
    """
    Get the sql_sha1 value from review_content filed in database.
    :param work_flow_id:
    :return:
    """
    work_flow_detail = Work.query.filter(Work.id == work_flow_id).first()
    dict_sha1 = {}

    # Transfer review_content from str to list object.
    list_recheck_result = json.loads(work_flow_detail.auto_review)

    for row_num in range(len(list_recheck_result)):
        id = row_num + 1
        sql_sha1 = list_recheck_result[row_num][10]
        if sql_sha1 != '':
            dict_sha1[id] = sql_sha1

    if dict_sha1 != {}:
        # Make dict_sha1 as the value and the work_flow_id as the key
        # And put them into the global dictionary sql_sha1_cache which marked as cache
        # Because the pt-osc rarely used, the cache didn't set timeout limitation
        sql_sha1_cache[work_flow_id] = dict_sha1

    return dict_sha1


@audit.route('/osc_percent', methods=['POST'])
def osc_percent():
    """
    Get pt-osc percentage and remain time.
    :return:
    """
    work_flow_id = request.form['workflowid']
    sql_id = request.form['sqlID']

    if work_flow_id == '' and work_flow_id is None or sql_id == '' or sql_id is None:
        context = {'status': -1, 'msg': 'workflowId or sqlID is null !', 'data': ''}

        return jsonify(context)

    work_flow_id = int(work_flow_id)
    sql_id = int(sql_id)

    if work_flow_id in sql_sha1_cache:
        dict_sha1 = sql_sha1_cache[work_flow_id]
    else:
        dict_sha1 = get_sql_sha1(work_flow_id)

    if dict_sha1 != {} and sql_id in dict_sha1:
        sql_sha1 = dict_sha1[sql_id]

        # Query the percentage through Inception from the sha1
        result = get_osc(sql_sha1)

        if result["status"] == 0:
            pct_result = result

            return jsonify(pct_result)
        else:
            execute_result = Work.query.filter(Work.id == work_flow_id).first().execute_result
            try:
                list_execute_result = json.loads(execute_result)
            except:
                list_execute_result = execute_result

            if type(list_execute_result) == list and len(list_execute_result) >= sql_id - 1:

                if dict_sha1[sql_id] in list_execute_result[sql_id - 1][10]:
                    pct_result = {'status': 0, 'msg': 'ok', 'data': {'percent': 100, 'time_remain': ''}}

                    return jsonify(pct_result)
            else:
                pct_result = {'status': -3, 'msg': 'Progress Unknown', 'data': {'percent': -100, 'time_remain': ''}}

                return jsonify(pct_result)

    elif dict_sha1 != {} and sql_id not in dict_sha1:
        pct_result = {'status': 4, 'msg': '该行sql不由pt-OSC执行', 'data': ''}

        return jsonify(pct_result)
    else:
        pct_result = {'status': -2, 'msg': '整个工单不由pt-OSC执行', 'data': ''}

        return jsonify(pct_result)


@audit.route('/stop_osc', methods=['POST'])
@audit_permission.require(http_exception=403)
def stop_osc_progress():
    """
    Stop pt-osc across to sha1.
    :return:
    """
    data = request.form
    work_flow_id = data['workflowid']
    sql_id = data['sqlID']

    if work_flow_id == '' or work_flow_id is None or sql_id == '' or sql_id is None:
        context = {"status": -1, 'msg': 'workflowId或sqlID参数为空.', "data": ""}

        return jsonify(context)

    work_flow_detail = Work.query.filter(Work.id == work_flow_id).first()

    if work_flow_detail.status != 3:
        context = {'status': -1, 'msg': '当前工单状态不是执行中，请刷新当前页面！', 'data': ""}

        return jsonify(context)

    work_flow_id = int(work_flow_id)
    sql_id = int(sql_id)

    if work_flow_id in sql_sha1_cache:
        dict_sha1 = sql_sha1_cache[work_flow_id]
    else:
        dict_sha1 = get_sql_sha1(work_flow_id)

    if dict_sha1 != {} and sql_id in dict_sha1:
        sql_sha1 = dict_sha1[sql_id]
        opt_result = stop_osc(sql_sha1)
    else:
        opt_result = {'status': 4, 'msg': '不是由pt-OSC执行的', 'data': ""}

    return jsonify(opt_result)


@audit.route('/work_flow_status', methods=['POST'])
def work_flow_status():
    """
    Deal with the get work status request from Ajax
    :return:
    """
    work_flow_id = request.form['workflowid']

    if work_flow_id == '' or work_flow_id is None:
        context = {'status': -1, 'msg': 'workflowId参数为空', 'data': ''}

        return jsonify(context)

    work_flow_id = int(work_flow_id)
    work_flow_detail = Work.query.get(work_flow_id)
    work_flow_status = work_flow_detail.status

    result = {'status': work_flow_status, 'msg': '', 'data': ''}

    return jsonify(result)


@audit.route('/audit/work/rollback/<int:id>')
@audit_permission.require(http_exception=403)
def audit_work_rollback(id):
    """
    Roll back sql.
    :param id:
    :return:
    """
    sql_roll = get_sql_roll(id)
    base_dir = os.path.dirname(__file__)
    roll_back_dir = base_dir + '/tmp'

    if not os.path.exists(roll_back_dir):
        os.makedirs(roll_back_dir)
    fp = open(roll_back_dir + '/roll_back.sql', 'w')

    for i in range(len(sql_roll)):
        fp.write(sql_roll[i] + '\n')
    fp.close()

    response = make_response(send_file(roll_back_dir + '/roll_back.sql'))
    response.headers['Content-Disposition'] = "attachment; filename=ex.sql"

    return response
