#!/usr/bin/env python3
import sys

sys.path.append('..')  # fix import directory

from app import db
from app import app

with app.app_context():
  db.create_all()
