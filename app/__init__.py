"""
    ustc courses

    :copyright: (c) 2015 by the USTC-Courses Team.

"""

import os
from flask import Flask,request
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager
from flask_wtf.csrf import CsrfProtect
from flask.ext.babel import Babel

app = Flask(__name__)
app.config.from_object('config.default')


db = SQLAlchemy(app)
CsrfProtect(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'home.signin'

babel = Babel(app)
@babel.localeselector
def get_locale():
    return request.accept_languages.best_match(app.config['LANGUAGES'].keys())


from app.views import *
app.register_blueprint(home,url_prefix='')
app.register_blueprint(course,url_prefix='/course')
app.register_blueprint(review, url_prefix='/review')
app.register_blueprint(api, url_prefix='/api')
app.register_blueprint(user, url_prefix='/user')

