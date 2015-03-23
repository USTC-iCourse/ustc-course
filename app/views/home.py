from flask import Blueprint,request, redirect,url_for,render_template,flash
from flask.ext.login import login_user, login_required
from app.models import User
from app.forms import LoginForm, RegisterForm


home = Blueprint('home',__name__)

@home.route('/')
@login_required
def index():
    return redirect(url_for('course.index'))

@home.route('/login/',methods=['POST','GET'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        #validate uesr
        login_user(user)
        flash('Logged in')
        return redirect(request.args.get('next') or url_for('home.index'))
    return render_template('login.html',form=form)


@home.route('/register/',methods=['GET','POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email = request.form.get('email')
        password = request.form.get('password')
        user = User(email=email,password=password)
        user.save()
        flash('registered')
        return redirect(request.args.get('next') or url_for('.index'))
    if form.errors:
        print(form.errors)
    return render_template('register.html',form=form)


