import base64

from flask import current_app

from .models import Dbconfig


def sql_auto_review(sql_content, db_in_name, is_split="no"):
    """
    SQL Auto Review via Inception
    """
    db_in = Dbconfig.query.filter(Dbconfig.name == db_in_name).first()
    db_host = db_in.master_host
    db_port = db_in.master_port
    db_user = db_in.username
    db_password = base64.b64decode(db_in.password)

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
                # 这种场景只给osc进度功能使用
                # 如果一个工单中同时包含DML和DDL，那么执行时被split后的SQL与提交的SQL会不一样（会在每条语句前面加use database;)，导致osc进度更新取不到正确的SHA1值。
                # 请参考inception文档中--enable-split参数的说明
                sql_split = "/*--user=%s; --password=%s; --host=%s; --enable-execute;--port=%s; --enable-ignore-warnings;--enable-split;*/\
                             inception_magic_start;\
                             %s\
                             inception_magic_commit;" % (db_user, db_password, db_host, str(db_port), sql_content)
                split_result = fetchall(sql_split, current_app.config['INCEPTION_HOST'],
                                        current_app.config['INCEPTION_PORT'], '', '', '')
                tmp_list = []
                for split_row in split_result:
                    sql_tmp = split_row[1]
                    sql = "/*--user=%s;--password=%s;--host=%s;--enable-check;--port=%s; --enable-ignore-warnings;*/\
                            inception_magic_start;\
                            %s\
                            inception_magic_commit;" % (db_user, db_password, db_host, str(db_port), sql_tmp)
                    review_result = fetchall(sql, current_app.config['INCEPTION_HOST'],
                                             current_app.config['INCEPTION_PORT'], '', '', '')
                    tmp_list.append(review_result)

                # 二次加工下
                final_list = []
                for split_row in tmp_list:
                    for sql_row in split_row:
                        final_list.append(list[sql_row])
                result = final_list
            else:
                # 工单审核使用
                sql = "/*--user=%s;--password=%s;--host=%s;--enable-check=1;--port=%s;*/\
                        inception_magic_start;\
                        %s\
                        inception_magic_commit;" % (db_user, db_password, db_host, str(db_port), sql_content)
                result = fetchall(sql, current_app.config['INCEPTION_HOST'], current_app.config['INCEPTION_PORT'], '',
                                  '', '')

    return result
