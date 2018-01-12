# Incepiton Mysql

:apple: A web platform designed for MySQL Inception.

![Travis](https://img.shields.io/badge/python-v3.x-orange.svg)
![Travis](https://img.shields.io/badge/flask-v0.12.2-orange.svg)
![Travis](https://img.shields.io/badge/mysql-v5.7-orange.svg)
![Travis](https://img.shields.io/badge/celery-v4.0.1-orange.svg)
![Travis](https://img.shields.io/badge/latest--version-v1.0.0-green.svg)
![Travis](https://img.shields.io/badge/downloads-1k-green.svg)
![Travis](https://img.shields.io/badge/license-MIT-blue.svg)


## 功能一览

### 登陆

登陆流程分两种，一种对接企业内部的OpenLDAP，实现账号统一管理。另一种是直接走数据库。两种方式的选择通过<code>config.py</code>中的<code>LDAP_ON_OFF</code>控制

### 权限管理

分三种角色。Dev，开发人；Audit，审核人；Admin，管理员

### Dev功能

- 数据库实例查看、申请、取消
- 工单查看、申请、取消、修改
- 工单状态、数目可视化展示

### Audit功能

- 数据库实例查看、分配、撤销
- 工单查看、取消、驳回、执行、定时执行
- 支持 pt-online-schema-change 工具，大表可进行 online DDL操作
- SQL执行进度实时获取，中途可停止，需手动清除触发器和临时表

### Admin功能

- 数据库实例添加、修改、删除
- 用户添加、修改、删除

### 邮件通知

## 重要功能介绍

### 支持分表操作

![分表操作](https://github.com/Tianny/incepiton_mysql/blob/master/images/work_create.png)

### 自动审核

发起SQL上线，由[Inception](https://github.com/mysql-inception/inception)自动审核，自动审核成功后，提交至Audit。

![自动审核结果](https://github.com/Tianny/incepiton_mysql/blob/master/images/auto_check.png)

### 审核人操作
![审核人操作](https://github.com/Tianny/incepiton_mysql/blob/master/images/audit_operate.png)

### SQL执行进度实时获取

只有走pt-osc修改大表时，才会显示执行进度。具体多大的表走pt-osc，可以通过 Inception 来配置，具体参考 [Inception文档](http://mysql-inception.github.io/inception-document/)。
![进度获取](https://github.com/Tianny/incepiton_mysql/blob/master/images/percent.png)

### 定时任务

定时任务可设置、取消
![定时任务](https://github.com/Tianny/incepiton_mysql/blob/master/images/timer.png)


### 工单图表
![图表](https://github.com/Tianny/incepiton_mysql/blob/master/images/chart.png)

### 回滚操作
![回滚](https://github.com/Tianny/incepiton_mysql/blob/master/images/result.png)

## 资源状态说明

- 0：Success，成功
- 1：Pending，未处理
- 2：Dev Cancelled，开发人取消
- 3：Audit Cancelled，审核人取消

## 工单状态说明

- 0：Success，成功
- 1：Pending， 带人工审核
- 2：Check Failed，自动审核失败
- 3：Executing，执行中
- 4：Error，执行异常
- 5：Dev Cancelled，开发人取消
- 6：Audit Cancelled，审核人取消
- 7：Audit Rejected，审核人驳回
- 8：Timer，定时任务

## 部分开发说明

1. Inception编译安装，请使用 bison 2.6 以下版本

2. 请注意 Python3 和 Python2 编码不同

3. 对接OpenLDAP，使用了[flask-simpleLDAP](http://flask-simpleldap.readthedocs.io/en/latest/)扩展，为了兼容 python3，有一处源码需要修改，__init.__py 第153行，按如下修改
![ldap](https://github.com/Tianny/incepiton_mysql/blob/master/images/flask-ldap-modify.png)

4. 为了兼容 Inception 返回的信息，pyMysql 需要修改两处源码。
- python3使用的pyMysql模块里并未兼容inception返回的server信息，因此需要添加
![2](https://github.com/Tianny/incepiton_mysql/blob/master/images/pymsql_modify_2.png)

- python3的pyMysql模块会向inception发送SHOW WARNINGS语句，导致inception返回一个"Must start as begin statement"错误。
![1](https://github.com/Tianny/incepiton_mysql/blob/master/images/pymsql_modify_1.png)

5. Celery 最新版本即4.0.1 存在时区设置BUG，具体详见[TimeZone Bug](https://github.com/celery/celery/pull/4173/)，具体就是设置了 Asia/Shanghai，ETA 执行的时间比正常东八区时间又多了8个小时，不过我已经在代码里处理过了。官方会在下个版本修复。

## 使用说明

- 创建表结构
```python
python manage.py shell
db.creat_all()
```
- 创建用户

如果是走OpenLDAP的话，不需要手动创建用户，会自动同步到数据库中。

不走OpenLDAP，通过登录页面的注册功能即可。当然也可手动去数据库里添加。

- 部署

Flask部署方式请Google

- 本地测试

```python
python manage.py run server --threaded
```