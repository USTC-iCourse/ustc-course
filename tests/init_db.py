#!/usr/bin/env python3
import sys
sys.path.append('..')  # fix import directory

from app import app, db
with app.app_context():
    db.create_all()
