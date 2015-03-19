from flask import Blueprint,redirect,url_for,render_template
from flask.ext.security import login_required


home = Blueprint('home',__name__)

@home.route('/')
@login_required
def index():
    return render_template('index.html')
    return redirect(url_for('course.index'))
