# Server config
SERVER_NAME = None
DEBUG = True
SECRET_KEY = 'secret-key'


# available languages
LANGUAGES = {
        'en': 'English',
        'zh': '中文'
        }


# SQL config
#SQLALCHEMY_DATABASE_URI = 'mysql+mysqldb://ustc_course:ustc_course@localhost/icourse?charset=utf8'
SQLALCHEMY_DATABASE_URI = 'mysql+mysqldb://ustc_course:ustc_course@202.141.160.99:44712/icourse?charset=utf8'

# Flask mail
MAIL_SERVER = 'localhost'
MAIL_PORT = 25
MAIL_USE_TLS = False
MAIL_USE_SSL = False
MAIL_DEBUG = DEBUG
MAIL_USERNAME = None
MAIL_PASSWORD = None
MAIL_DEFAULT_SENDER = 'support@icourse.freeshell.ustc.edu.cn'
MAIL_MAX_EMAILS = None
#MAIL_SUPPRESS_SEND =
MAIL_ASCII_ATTACHMENTS = False

# Upload config
UPLOAD_FOLDER = '/tmp/uploads'
# Alowed extentsions for a filetype
# for example 'image': set(['png', 'jpg', 'jpeg', 'gif'])
ALLOWED_EXTENSIONS = {
        'image':set(['png', 'jpg', 'jpeg', 'gif'])
        }



IMAGE_PATH = 'uploads/images'


# Debugbar Settings
# Enable the profiler on all requests
DEBUG_TB_PROFILER_ENABLED = True
# Enable the template editor
DEBUG_TB_TEMPLATE_EDITOR_ENABLED =True
DEBUG_TB_INTERCEPT_REDIRECTS = False
