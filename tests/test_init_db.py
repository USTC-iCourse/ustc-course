#!/usr/bin/env python3

# A SQLite database will be created at /tmp/test.db
# If you want to clear the database, just delete /tmp/test.db

import sys
sys.path.append('..')  # fix import directory

from app import app,db
from app.models import *
from random import randint

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'

db.create_all()
