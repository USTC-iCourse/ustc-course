# Gunicorn configuration file
import logging
import sys

# Bind to localhost
bind = "127.0.0.1:3000"

# Number of workers
workers = 32

# Logging
accesslog = "/var/log/ustc-course/ustc-course-access.log"
errorlog = "/var/log/ustc-course/ustc-course-error.log"
loglevel = "info"

# Capture print statements and errors
capture_output = True

# Log to stdout as well (for systemd journal)
logconfig_dict = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'generic': {
            'format': '%(asctime)s [%(process)d] [%(levelname)s] %(message)s',
            'datefmt': '[%Y-%m-%d %H:%M:%S %z]',
            'class': 'logging.Formatter'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'generic',
            'stream': sys.stdout
        },
        'error_file': {
            'class': 'logging.FileHandler',
            'formatter': 'generic',
            'filename': errorlog
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'error_file']
    },
    'loggers': {
        'gunicorn.error': {
            'level': 'INFO',
            'handlers': ['console', 'error_file'],
            'propagate': False
        },
        'gunicorn.access': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False
        }
    }
}

