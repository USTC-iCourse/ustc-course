# Server config
DEBUG = False
SECRET_KEY = 'secret-key'



# SQL config
SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/test.db'


# Flask mail
MAIL_SERVER = 'localhost'
MAIL_PORT = 25
MAIL_USE_TLS = False
MAIL_USE_SSL = False
MAIL_DEBUG = DEBUG
MAIL_USERNAME = None
MAIL_PASSWORD = None
MAIL_DEFAULT_SENDER = 'test@ibat.me'
MAIL_MAX_EMAILS = None
#MAIL_SUPPRESS_SEND =
MAIL_ASCII_ATTACHMENTS = False
