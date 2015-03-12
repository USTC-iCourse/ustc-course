from datetime import datetime

from flask import url_for,abort
from app import db

class Course(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(40))
    #TODO: other proberty


