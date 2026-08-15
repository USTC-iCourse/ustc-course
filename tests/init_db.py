#!/usr/bin/env python3
import sys
sys.path.append('..')  # fix import directory

from app import app, db
from app.search import builder

with app.app_context():
    db.create_all()
    # Search reads a memory-mapped index, not the database, and returns 503
    # until one exists.  Building it here keeps a fresh install working out of
    # the box; on an empty database it is instant.
    for stats in (builder.build(app, db, name) for name in sorted(builder.ALL)):
        print('search index: %(collection)s, %(documents)d documents -> %(path)s' % stats)
