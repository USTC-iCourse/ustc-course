from flask import Blueprint,render_template,abort,redirect,url_for,request,abort,jsonify
from flask_login import login_required
from flask_babel import gettext as _
from app.models import *
from app import db
from app.utils import sanitize
from sqlalchemy import or_, func

data = Blueprint('data',__name__)


@data.route('/')
def index():
    user_rank = User.query.limit(5).all()
    return render_template('data.html', users=user_rank)


@data.route('/teachers')
def teacher_ranking():
    return render_template('data.html')


@data.route('/users')
def user_ranking():
    return render_template('data.html')


@data.route('/reviews')
def review_ranking():
    return render_template('data.html')


@data.route('/history')
def view_history():
    return render_template('data.html')
