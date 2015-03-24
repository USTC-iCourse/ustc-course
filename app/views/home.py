from flask import Blueprint,request, redirect,url_for,render_template,flash
from flask.ext.login import login_user, login_required, current_user, logout_user
from app.models import User
from app.forms import LoginForm, RegisterForm


home = Blueprint('home',__name__)

@home.route('/')
def index():
    return redirect(url_for('course.index'))

@home.route('/signin/',methods=['POST','GET'])
def login():
    if current_user.is_authenticated():
        return redirect(url_for('.index',username=current_user.username))
    form = LoginForm()
    error = ''
    if form.validate_on_submit():
        user,status = User.authenticate(form['username'].data,form['password'].data)
        if user and status:
            #validate uesr
            login_user(user)
            flash('Logged in')
            print('logged in')
            return redirect(request.args.get('next') or url_for('home.index'))
        error = '用户名或密码错误'
    print(form.errors)
    return render_template('signin.html',form=form, error=error)


@home.route('/signup/',methods=['GET','POST'])
def signup():
    form = RegisterForm()
    if form.validate_on_submit():
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        user = User(username=username, email=email,password=password)
        user.save()
        flash('registered')
        return redirect(request.args.get('next') or url_for('.index'))
    if form.errors:
        print(form.errors)
    return render_template('signup.html',form=form)


@home.route('/logout/')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home.index'))


@home.route('/reset-password/', methods=['GET','POST'])
def reset_password():
    ''' 重置密码'''

    return render_template('reset-password.html')


@home.route('/report-bug/')
def report_bug():
    ''' 报bug表单 '''

    return render_template('report-bug.html')
