# Incepiton Mysql

:apple: A web platform designed for MySQL Inception.

![Travis](https://img.shields.io/badge/python-v3.x-orange.svg)
![Travis](https://img.shields.io/badge/flask-v0.12.2-orange.svg)
![Travis](https://img.shields.io/badge/mysql-v5.7-orange.svg)
![Travis](https://img.shields.io/badge/celery-v4.0.1-orange.svg)
![Travis](https://img.shields.io/badge/latest--version-v1.0.0-green.svg)
![Travis](https://img.shields.io/badge/downloads-1k-green.svg)
![Travis](https://img.shields.io/badge/license-MIT-blue.svg)


## 主要功能

### 登陆

登陆流程分两种，一种对接企业内部的OpenLDAP，实现账号统一管理。另一种是直接走数据库。两种方式的选择通过<code>config.py</code>中的<code>LDAP_ON_OFF</code>控制

### 权限管理

分三种角色。Dev，开发人；Audit，审核人；Admin，管理员

### Dev功能

- 数据库实例查看、申请、取消
- 工单查看、取消、

