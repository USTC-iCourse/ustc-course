#!/usr/bin/env python3
from app import app
from app import db
from random import randint
from app.models import Review, Course, Student, User

debug = True

def start():
    if debug:
        db.create_all()
    app.run(port=8080)



if __name__ == '__main__':
    start()
