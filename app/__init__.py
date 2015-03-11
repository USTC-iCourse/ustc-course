"""
    ustc courses

    :copyright: (c) 2015 by the USTC-Courses Team.

"""

import os
from flask import Flask,request
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from app.course import course
from app.home import home

app = Flask(__name__)

    #TODO: config file
    #app.config.from_object('config')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////'+os.path.join(app.root_path, 'test.db')

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
#login_manager.login_view = 'signin'


app.register_blueprint(home,url_prefix='')
app.register_blueprint(course,url_prefix='/course')


