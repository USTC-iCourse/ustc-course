# Gunicorn configuration file

# Bind to localhost
bind = "127.0.0.1:3000"

# Number of workers
workers = 32

# Logging
accesslog = "/var/log/ustc-course/ustc-course-access.log"
errorlog = "/var/log/ustc-course/ustc-course-error.log"
loglevel = "info"

# Capture stray print()/stderr from the app into the error log (safety net).
capture_output = True

# Send access logs and error/app logs to SEPARATE files.
# access -> access_file, error/app -> error_file. No console handler:
# under capture_output the process stdout/stderr is already redirected to
# the error log, so a console handler would just duplicate everything there.
logconfig_dict = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'generic': {
            'format': '%(asctime)s [%(process)d] [%(levelname)s] %(message)s',
            'datefmt': '[%Y-%m-%d %H:%M:%S %z]',
            'class': 'logging.Formatter'
        },
        'access': {
            # gunicorn's access_log_format already includes time/status/etc.
            'format': '%(message)s',
            'class': 'logging.Formatter'
        }
    },
    'handlers': {
        'error_file': {
            'class': 'logging.FileHandler',
            'formatter': 'generic',
            'filename': errorlog
        },
        'access_file': {
            'class': 'logging.FileHandler',
            'formatter': 'access',
            'filename': accesslog
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['error_file']
    },
    'loggers': {
        'gunicorn.error': {
            'level': 'INFO',
            'handlers': ['error_file'],
            'propagate': False
        },
        'gunicorn.access': {
            'level': 'INFO',
            'handlers': ['access_file'],
            'propagate': False
        }
    }
}
