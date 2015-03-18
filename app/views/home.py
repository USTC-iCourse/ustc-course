from flask import Blueprint,redirect,url_for,render_template

home = Blueprint('home',__name__)

@home.route('/')
def index():
    return render_template('index.html')
    return redirect(url_for('course.index'))
