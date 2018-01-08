import base64
import re
import json
from datetime import datetime

import pymysql
from flask import current_app

from . import db
from .models import Dbconfig, Work


def fetch_all(sql_content, host, port, user, password, db_in):
    """
    封装mysql连接和获取结果集方法
    :param sql_content:
    :param host:
    :param port:
    :param user:
    :param password:
    :param db_in:
    :return:
    """
    result = None
    conn = None
    cur = None
    sql_content = sql_content.encode('utf-8').decode('utf-8')

    try:
        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            db=db_in,
            port=port,
            charset='utf8mb4'
        )
        cur = conn.cursor()
        cur.execute(sql_content)
        result = cur.fetchall()
    except pymysql.InternalError as e:
        print("Mysql Error %d: %s" % (e.args[0], e.args[1]))
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()

    return result


def critical_ddl(sql_content):
    """
    识别DROP DATABASE, DROP TABLE, TRUNCATE PARTITION, TRUNCATE TABLE等高危DDL操作，因为对于这些操作，
    inception在备份时只能备份METADATA，而不会备份数据！
    如果识别到包含高危操作，则返回“审核不通过”
    """
    result_list = []
    critical_sql_found = 0

    for row in sql_content.rstrip(';').split(';'):
        if re.match(
                r"([\s\S]*)drop(\s+)database(\s+.*)|([\s\S]*)drop(\s+)table(\s+.*)|([\s\S]*)truncate(\s+)partition(\s+.*)|([\s\S]*)truncate(\s+)table(\s+.*)",
                row.lower()
        ):
            result = (
                '',
                '',
                2,
                'Reject High Danger SQL',
                'Can not contain【DROP DATABASE】|【DROP TABLE】|【TRUNCATE PARTITION】|【TRUNCATE TABLE】keywords！',
                row,
                '',
                '',
                '',
                ''
            )
            critical_sql_found = 1
        else:
            result = ('', '', 0, '', 'None', row, '', '', '', '')
        result_list.append(result)

    if critical_sql_found == 1:
        return result_list
    else:
        return None


def pre_check(sql_content):
    """
    在提交给inception之前，预先识别一些Inception不能正确审核的SQL
    比如"alter table t1;"或"alter table test.t1;"
    以免导致inception core dump
    :param sql_content:
    :return:
    """
    result_list = []
    syntax_error_sql_found = 0
    for row in sql_content.rstrip(';').split(';'):
        if re.match(
                r"(\s*)alter(\s+)table(\s+)(\S+)(\s*);|(\s*)alter(\s+)table(\s+)(\S+)\.(\S+)(\s*);",
                row.lower() + ";"
        ):
            result = ('', '', 2, 'SQL语法错误', 'ALTER must have options', row, '', '', '', '')
            syntax_error_sql_found = 1
        else:
            result = ('', '', 0, '', 'None', row, '', '', '', '')

        result_list.append(result)

    if syntax_error_sql_found == 1:
        return result_list
    else:
        return None


def sql_auto_review(sql_content, db_in_name, is_split="no"):
    """
    SQL Auto Review via Inception
    """
    db_in = Dbconfig.query.filter(Dbconfig.name == db_in_name).first()
    db_host = db_in.master_host
    db_port = db_in.master_port
    db_user = db_in.username
    db_password = base64.b64decode(db_in.password.encode('utf-8'))
    db_password = db_password.decode('utf-8')

    critical_ddl_config = current_app.config['CRITICAL_DDL_ON_OFF']

    if critical_ddl_config == "ON":
        critical_ddl_check = critical_ddl(sql_content)
    else:
        critical_ddl_check = None

    if critical_ddl_check is not None:
        result = critical_ddl_check
    else:
        pre_check_result = pre_check(sql_content)
        if pre_check_result is not None:
            result = pre_check_result
        else:
            if is_split == 'yes':
                # 这种场景只给osc进度条功能使用
                # 如果一个工单中同时包含DML和DDL，那么执行时被split后的SQL与提交的SQL会不一样（会在每条语句前面加use database;)，
                # 导致osc进度更新取不到正确的SHA1值
                # 请参考inception文档中--enable-split参数的说明
                sql_split = "/*--user=%s; --password=%s; --host=%s; --enable-execute;--port=%s; --enable-ignore-warnings;--enable-split;*/\
                             inception_magic_start;\
                             %s\
                             inception_magic_commit;" % (db_user, db_password, db_host, str(db_port), sql_content)
                split_result = fetch_all(sql_split, current_app.config['INCEPTION_HOST'],
                                         current_app.config['INCEPTION_PORT'], '', '', '')
                tmp_list = []

                for split_row in split_result:
                    sql_tmp = split_row[1]
                    sql = "/*--user=%s;--password=%s;--host=%s;--enable-check;--port=%s; --enable-ignore-warnings;*/\
                            inception_magic_start;\
                            %s\
                            inception_magic_commit;" % (db_user, db_password, db_host, str(db_port), sql_tmp)
                    review_result = fetch_all(sql, current_app.config['INCEPTION_HOST'],
                                              current_app.config['INCEPTION_PORT'], '', '', '')
                    tmp_list.append(review_result)

                # 二次加工下
                final_list = []

                for split_row in tmp_list:
                    for sql_row in split_row:
                        final_list.append(list(sql_row))
                result = final_list
            else:
                # 工单审核使用
                sql = "/*--user=%s;--password=%s;--host=%s;--enable-check=1;--port=%s;*/\
                        inception_magic_start;\
                        %s\
                        inception_magic_commit;" % (db_user, db_password, db_host, str(db_port), sql_content)
                result = fetch_all(sql, current_app.config['INCEPTION_HOST'], current_app.config['INCEPTION_PORT'], '',
                                   '', '')

    return result


def execute_final(app, id):
    """
    将sql交给inception进行最终执行，并返回结果
    :param app:
    :param id:
    :return:
    """
    with app.app_context():
        work = Work.query.filter(Work.id == id).first()
        db_in = Dbconfig.query.filter(Dbconfig.name == work.db_name).first()
        db_host = db_in.master_host
        db_port = db_in.master_port
        db_user = db_in.username
        db_password = base64.b64decode(db_in.password.encode('utf-8'))
        db_password = db_password.decode('utf-8')

        if work.backup == True:
            str_backup = "--enable-remote-backup;"
        else:
            str_backup = "--disable-remote-backup;"

        # 根据inception要求，执行前最好先spilt一下
        sql_split = "/*--user=%s; --password=%s; --host=%s; --enable-execute;--port=%s; --enable-ignore-warnings;--enable-split;*/\
             inception_magic_start;\
             %s\
             inception_magic_commit;" % (db_user, db_password, db_host, str(db_port), work.sql_content)
        spilt_result = fetch_all(sql_split, current_app.config['INCEPTION_HOST'], current_app.config['INCEPTION_PORT'],
                                 '', '', '')
        tmp_list = []

        # 对split好的结果，再次交给inception执行。这里无需保持长连接执行，短连接即可
        for split_row in spilt_result:
            sql_tmp = split_row[1]
            sql_execute = "/*--user=%s;--password=%s;--host=%s;--enable-execute;--port=%s; --enable-ignore-warnings;%s*/\
                                inception_magic_start;\
                                %s\
                                inception_magic_commit;" % (
                db_user, db_password, db_host, str(db_port), str_backup, sql_tmp)

            execute_result = fetch_all(sql_execute, current_app.config['INCEPTION_HOST'],
                                       current_app.config['INCEPTION_PORT'], '', '', '')

            for sql_row in execute_result:
                tmp_list.append(sql_row)

            # 每执行一次，就将执行结果更新到工单的execute_result，便于获取osc进度时对比
            work.execute_result = json.dumps(tmp_list)
            db.session.add(work)
            db.session.commit()

        # 二次加工一下，目的是为了和sql_auto_review()函数的return保持格式一致，便于在detail页面渲染.
        final_status = 0
        final_list = []
        for sql_row in tmp_list:
            # 如果发现任何一个执行结果里有errLevel为1或2，并且stage_status列没有包含Execute Successfully字样，则判断为异常
            if (sql_row[2] == 1 or sql_row[2] == 2) and re.match(r"\w*Execute Successfully\w*", sql_row[3]) is None:
                final_status = 4
            final_list.append(list(sql_row))

        json_result = json.dumps(final_list)
        work.execute_result = json_result
        work.finish_time = datetime.now()
        work.status = final_status

        db.session.add(work)
        db.session.commit()


def get_osc(sql_sha1):
    sql_str = "inception get osc_percent '%s'" % sql_sha1
    result = fetch_all(sql_str, current_app.config['INCEPTION_HOST'], current_app.config['INCEPTION_PORT'], '', '', '')
    if len(result) > 0:
        percent = result[0][3]
        time_remain = result[0][4]
        pct_result = {'status': 0, 'msg': 'ok', 'data': {'percent': percent, 'time_remain': time_remain}}
    else:
        pct_result = {'status': 1, 'msg': '没找到该SQL的进度信息，是否已经执行完毕？', 'data': {'percent': -100, 'time_remain': -100}}

    return pct_result


def stop_osc(sql_sha1):
    """已知SHA1值，调用inception命令停止OSC进程，涉及的Inception命令和注意事项
    请参考http://mysql-inception.github.io/inception-document/osc/
    """
    sql_str = "inception stop alter '%s'" % sql_sha1
    result = fetch_all(sql_str, current_app.config['INCEPTION_HOST'], current_app.config['INCEPTION_PORT'], '', '', '')
    if result is not None:
        opt_result = {'status': 0, 'msg': '已成功停止OSC进程，请注意清理触发器和临时表', 'data': ""}
    else:
        opt_result = {'status': 1, 'msg': 'ERROR 2624 (HY000):未找到OSC执行进程，可能已经执行完成', 'data': ""}

    return opt_result


def get_sql_roll(work_id):
    work = Work.query.get(work_id)
    execute_result = json.loads(work.execute_result)
    sql_roll = []
    for row in execute_result:
        if row[8] == 'None':
            continue
        backup_db_name = row[8]
        sequence = row[7]
        opid_time = sequence.replace("'", "")
        sql_table = "select tablename from %s.$_$Inception_backup_information$_$ where opid_time='%s';" % (
            backup_db_name, opid_time)
        tables = fetch_all(
            sql_table,
            current_app.config['INCEPTION_REMOTE_BACKUP_HOST'],
            current_app.config['INCEPTION_REMOTE_BACKUP_PORT'],
            current_app.config['INCEPTION_REMOTE_BACKUP_USER'],
            current_app.config['INCEPTION_REMOTE_BACKUP_PASSWORD'],
            ''
        )
        if tables is None or len(tables) != 1:
            print('Error: return list_tables more than 1')

        table_name = tables[0][0]
        sql_back = "select rollback_statement from %s.%s where opid_time='%s'" % (backup_db_name, table_name, opid_time)

        backups = fetch_all(
            sql_back,
            current_app.config['INCEPTION_REMOTE_BACKUP_HOST'],
            current_app.config['INCEPTION_REMOTE_BACKUP_PORT'],
            current_app.config['INCEPTION_REMOTE_BACKUP_USER'],
            current_app.config['INCEPTION_REMOTE_BACKUP_PASSWORD'],
            ''
        )

        if backups is not None and len(backups) != 0:
            for row_num in range(len(backups)):
                sql_roll.append(backups[row_num][0])

    return sql_roll
