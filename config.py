import os


class Config:
    """
    Configurations shared by all env.
    """

    SECRET_KEY = os.getenv('SECRET_KEY', 'THIS IS AN INSECURE SECRET')
    CSRF_ENABLED = True

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask-Mail settings
    MAIL_ON_OFF = 'OFF'
    MAIL_SERVER = 'smtp.163.com'
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = '"inception"<inception_notice@163.com>'

    # Inception DDL switch option
    CRITICAL_DDL_ON_OFF = 'ON'

    # LDAP switch option
    LDAP_ON_OFF = 'OFF'


class DevelopmentConfig(Config):
    """
    Configurations used for development env.
    """

    DEBUG = True

    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DEV_DATABASE_URL',
        'mysql+pymysql://root:mysql@127.0.0.1:3306/inception_web?charset=utf8'
    )

    # Inception settings
    INCEPTION_HOST = '127.0.0.1'
    INCEPTION_PORT = 6669

    # Inception backup settings
    INCEPTION_REMOTE_BACKUP_HOST = '127.0.0.1'
    INCEPTION_REMOTE_BACKUP_PORT = 3306
    INCEPTION_REMOTE_BACKUP_USER = 'root'
    INCEPTION_REMOTE_BACKUP_PASSWORD = 'mysql'

    # Flask LDAP settings
    LDAP_OPENLDAP = True
    LDAP_OBJECTS_DN = 'dn'
    LDAP_REALM_NAME = 'OpenLDAP Authentication'
    LDAP_HOST = '10.10.106.201'
    LDAP_BASE_DN = 'cn=users,cn=accounts,dc=in66,dc=cc'
    LDAP_USERNAME = ''
    LDAP_PASSWORD = ''
    LDAP_USER_OBJECT_FILTER = '(&(objectclass=inetOrgPerson)(uid=%s))'
    LDAP_LOGIN_VIEW = 'login'

    # Celery Broker setting
    CELERY_BROKER_URL = 'redis://127.0.0.1:6379'

    # Celery backend setting
    CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379'

    # Celery TimeZone
    # CELERY_ENABLE_UTC = False
    # CELERY_TIMEZONE = 'UTC'
    CELERY_TIMEZONE = 'Asia/Shanghai'

    # Celery other settings
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_TRACK_STARTED = True

    # Celery ETA/countdown setting for solving tasks executed again, and again in a loop
    BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 18000}  # 5 hours

    # Celery Tasks
    CELERY_IMPORTS = ("app.tasks",)


class TestingConfig(Config):
    pass


class ProductionConfig(Config):
    pass


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,

    'default': DevelopmentConfig
}
