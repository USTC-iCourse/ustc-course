#!/usr/bin/env python3
from app import app
from app import db
from random import randint
from app.models import Review, Course, Student, User
import sys

debug = False
for arg in sys.argv:
  if arg == '-d':
    debug = True


def start():
  if debug:
    db.create_all()
    app.run(port=2021, threaded=True, host='127.0.0.1')
  else:
    from waitress import serve
    serve(app, host="127.0.0.1", port=3000)
    # serve(app, host="127.0.0.1", port=8030)
    # app.run(port=8030, threaded=True)


if __name__ == '__main__':
  start()
