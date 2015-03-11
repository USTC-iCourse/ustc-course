from flask import Blueprint,redirect,url_for

home = Blueprint('home',__name__)

@home.route('/')
def index():
    return redirect(url_for('course.index'))
