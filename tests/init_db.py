#!/usr/bin/env python3
import sys
sys.path.append('..')  # fix import directory

from app import db
db.create_all()
