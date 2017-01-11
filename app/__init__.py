"""
    ustc courses

    :copyright: (c) 2015 by the USTC-Courses Team.

"""

import os
from flask import Flask,request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager,current_user,user_logged_in,user_loaded_from_cookie
from flask_wtf.csrf import CSRFProtect
from flask_babel import Babel
from datetime import datetime
from flask_debugtoolbar import DebugToolbarExtension


app = Flask(__name__)
app.config.from_object('config.default')

toolbar = DebugToolbarExtension(app)

db = SQLAlchemy(app)
app.csrf = CSRFProtect(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'home.signin'

babel = Babel(app)
@babel.localeselector
def get_locale():
    return request.accept_languages.best_match(app.config['LANGUAGES'].keys())

def log_login(app,user):
    '''update the last login time of the user'''
    user.last_login_time = datetime.utcnow()
    db.session.commit()

user_logged_in.connect(log_login)
user_loaded_from_cookie.connect(log_login)


from app.views import *
app.register_blueprint(home,url_prefix='')
app.register_blueprint(course,url_prefix='/course')
app.register_blueprint(review, url_prefix='/review')
app.register_blueprint(api, url_prefix='/api')
app.register_blueprint(user, url_prefix='/user')
app.register_blueprint(teacher, url_prefix='/teacher')
