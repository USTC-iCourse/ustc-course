"""
    ustc courses

    :copyright: (c) 2015 by the USTC-Courses Team.

"""

import os
from flask import Flask,request
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager


app = Flask(__name__)
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
    #TODO: config file
    #app.config.from_object('config')

#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////'+os.path.join(app.root_path, 'test.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
#login_manager.login_view = 'signin'

from app.views import course
from app.views import home
app.register_blueprint(home,url_prefix='')
app.register_blueprint(course,url_prefix='/course')


