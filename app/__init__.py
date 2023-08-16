"""
    ustc courses

    :copyright: (c) 2015 by the XJTU-Courses Team.

"""

import os
from flask import Flask, request, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, user_logged_in, user_loaded_from_cookie
from flask_wtf.csrf import CSRFProtect
from flask_babel import Babel
from datetime import datetime
from flask_debugtoolbar import DebugToolbarExtension
from flask_migrate import Migrate

app = Flask(__name__)
app.config.from_object('config.default')

if app.config['DEBUG']:
  app.config['WTF_CSRF_CHECK_DEFAULT'] = False
  app.config['RETURN_URL'] = 'http://localhost/signincallback/'

toolbar = DebugToolbarExtension(app)

db = SQLAlchemy(app)
app.csrf = CSRFProtect(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'home.signin'

migrate = Migrate(app, db)

def get_locale():
  return request.accept_languages.best_match(app.config['LANGUAGES'].keys())


babel = Babel(app, locale_selector=get_locale)


def log_login(app, user):
  '''update the last login time of the user'''
  user.last_login_time = datetime.utcnow()
  db.session.commit()


user_logged_in.connect(log_login)
user_loaded_from_cookie.connect(log_login)


class ReverseProxied(object):
  def __init__(self, app):
    self.app = app

  def __call__(self, environ, start_response):
    if 'DEBUG' not in app.config or not app.config['DEBUG']:
      environ['wsgi.url_scheme'] = 'https'
    return self.app(environ, start_response)


app.wsgi_app = ReverseProxied(app.wsgi_app)

from app.models import Banner


@app.context_processor
def inject_global_banner():
  banner = Banner.query.order_by(Banner.publish_time.desc()).first()
  global_time = {'date': datetime.utcnow()}
  if banner:
    global_time['banner'] = banner
  return global_time


@app.errorhandler(404)
def page_not_found(e):
  return render_template('error-page.html', code=404, error=e), 404


@app.errorhandler(403)
def page_not_found(e):
  return render_template('error-page.html', code=403, error=e), 403


@app.errorhandler(400)
def page_not_found(e):
  return render_template('error-page.html', code=400, error=e), 400


@app.errorhandler(500)
def page_not_found(e):
  return render_template('error-page.html', code=500, error=e), 500


@app.errorhandler(502)
def page_not_found(e):
  return render_template('error-page.html', code=502, error=e), 502


from app.views import *

app.register_blueprint(home, url_prefix='')
app.register_blueprint(course, url_prefix='/course')
app.register_blueprint(review, url_prefix='/review')
app.register_blueprint(api, url_prefix='/api')
app.register_blueprint(user, url_prefix='/user')
app.register_blueprint(teacher, url_prefix='/teacher')
app.register_blueprint(admin, url_prefix='/admin')
app.register_blueprint(stats, url_prefix='/stats')
app.register_blueprint(program, url_prefix='/program')
