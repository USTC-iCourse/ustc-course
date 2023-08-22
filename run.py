#!/usr/bin/env python3
from app import app
from app import db
from random import randint
from app.models import Review, Course, Student, User
import sys
debug = True
for arg in sys.argv:
  if arg == '-d':
    debug = True


def start():
    from waitress import serve
    serve(app, host="127.0.0.1", port=8110)
    # serve(app, host="127.0.0.1", port=8030)
    # app.run(port=8030, threaded=True)


if __name__ == '__main__':
  start()
