import os
import sys

# Server config
SERVER_NAME = None
DEBUG = False
for arg in sys.argv:
  if arg == '-d':
    DEBUG = True

SECRET_KEY = os.environ['COURSE_SECRET_KEY']
EMAIL_CONFIRM_SECRET_KEY = os.environ['COURSE_EMAIL_CONFIRM_SECRET_KEY']
PASSWORD_RESET_SECRET_KEY = os.environ['COURSE_PASSWORD_RESET_SECRET_KEY']

# available languages
LANGUAGES = {
  'en': 'English',
  'zh': '中文'
}

# SQL config
SQLALCHEMY_DATABASE_URI = os.environ['COURSE_SQLALCHEMY_DATABASE_URI']
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Flask mail
MAIL_SERVER = 'localhost'
MAIL_PORT = 25
MAIL_USE_TLS = False
MAIL_USE_SSL = False
MAIL_DEBUG = DEBUG
MAIL_USERNAME = None
MAIL_PASSWORD = None
MAIL_DEFAULT_SENDER = 'course-review-support@xjtu.live'
MAIL_MAX_EMAILS = None
# MAIL_SUPPRESS_SEND =
MAIL_ASCII_ATTACHMENTS = False

# Upload config
UPLOAD_FOLDER = '/var/course-uploads/'
# Alowed extentsions for a filetype
# for example 'image': set(['png', 'jpg', 'jpeg', 'gif'])
ALLOWED_EXTENSIONS = {
  'image': set(['png', 'jpg', 'jpeg', 'gif']),
  'file': set(
    '7z|avi|csv|doc|docx|flv|gif|gz|gzip|jpeg|jpg|mov|mp3|mp4|mpc|mpeg|mpg|ods|odt|pdf|png|ppt|pptx|ps|pxd|rar|rtf|tar|tgz|txt|vsd|wav|wma|wmv|xls|xlsx|xml|zip'.split(
      '|')),
}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024

IMAGE_PATH = 'uploads/images'

# Debugbar Settings
# Enable the profiler on all requests
DEBUG_TB_PROFILER_ENABLED = True
# Enable the template editor
DEBUG_TB_TEMPLATE_EDITOR_ENABLED = True
DEBUG_TB_INTERCEPT_REDIRECTS = False
