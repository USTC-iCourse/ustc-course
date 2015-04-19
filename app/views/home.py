from flask import Blueprint,request, redirect,url_for,render_template,flash, abort, jsonify
from flask.ext.login import login_user, login_required, current_user, logout_user
from app.models import User, RevokedToken as RT, Course, CourseRate
from app.forms import LoginForm, RegisterForm, ForgotPasswordForm, ResetPasswordForm
from app.utils import ts, send_confirm_mail, send_reset_password_mail
from flask.ext.babel import gettext as _
from datetime import datetime

home = Blueprint('home',__name__)

@home.route('/')
def index():
    return render_template('index.html')

@home.route('/signin/',methods=['POST','GET'])
def signin():
    next_url = request.args.get('next') or url_for('home.index')
    if current_user.is_authenticated():
        return redirect(next_url)
    form = LoginForm()
    error = ''
    if form.validate_on_submit():
        user,status = User.authenticate(form['username'].data,form['password'].data)
        remember = form['remember'].data
        if user:
            if status:
                #validate uesr
                login_user(user, remember=remember)
                flash('Logged in')
                if request.args.get('ajax'):
                    return jsonify(status=200, next=next_url)
                else:
                    return redirect(next_url)
            else:
                '''没有确认邮箱的用户'''
                message = 'Please activate your account by clicking link in your email! <a href=%s>Resend Email</a>'%url_for('.confirm_email',
                    email=user.email,
                    action='send')
                if request.args.get('ajax'):
                    return jsonify(status=403, msg=message)
                else:
                    return render_template('feedback.html', status=False, message=message)
        else:
            error = _('Username or password is wrong!')
    #TODO: log the form errors
    if request.args.get('ajax'):
        return jsonify(status=404, msg=error)
    else:
        return render_template('signin.html',form=form, error=error)


@home.route('/signup/',methods=['GET','POST'])
def signup():
    if current_user.is_authenticated():
        return redirect(request.args.get('next') or url_for('home.index'))
    form = RegisterForm()
    if form.validate_on_submit():
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        user = User(username=username, email=email,password=password)
        email_suffix = email.split('@')[-1]
        if email_suffix == 'mail.ustc.edu.cn':
            user.identity = 'Student'
        elif email_suffix == 'ustc.edu.cn':
            user.identity = 'Teacher'
            ok,message = user.bind_teacher(email)
            #TODO: deal with bind feedback
        else:
            #TODO: log Intenal error!
            pass
        send_confirm_mail(user.email)
        user.save()
        #login_user(user)
        '''注册完毕后显示一个需要激活的页面'''
        return render_template('feedback.html', status=True, message=_('Please activate your account by clicking link in your email.'))
#TODO: log error
    if form.errors:
        print(form.errors)
    return render_template('signup.html',form=form)


@home.route('/confirm-email/')
def confirm_email():
    if current_user.is_authenticated():
        #logout_user()
        return redirect(request.args.get('next') or url_for('home.index'))
    action = request.args.get('action')
    if action == 'confirm':
        token = request.args.get('token')
        if not token:
            return render_template('feedback.html', status=False, message=_('Token error!'))
        if RT.query.get(token):
            return render_template('feedback.html', status=False, message=_('Token has been used!'))
        RT.add(token)
        try:
            email = ts.loads(token, salt="email-confirm-key", max_age=86400)
        except:
            abort(404)

        user = User.query.filter_by(email=email).first_or_404()
        user.confirm()
        flash(_('Your email has been confirmed'))
        login_user(user)
        return redirect(url_for('home.index'))
    elif action == 'send':
        email = request.args.get('email')
        user = User.query.filter_by(email=email).first_or_404()
        print(user)
        if not user.confirmed:
            print(email)
            send_confirm_mail(email)
        return render_template('feedback.html', status=True, message=_('Email has been sent!'))
    else:
        abort(404)


@home.route('/logout/')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home.index'))

@home.route('/change-password/', methods=['GET'])
def change_password():
    '''在控制面板里修改密码'''
    if not current_user.is_authenticated():
        return redirect(url_for('home.signin'))
    send_reset_password_mail(current_user.email)
    return render_template('feedback.html', status=True, message=_('Reset password mail sent'))


@home.route('/reset-password/', methods=['GET','POST'])
def forgot_password():
    ''' 忘记密码'''
    if current_user.is_authenticated():
        return redirect(request.args.get('next') or url_for('home.index'))
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form['email'].data
        user = User.query.filter_by(email=email).first()
        if user:
            send_reset_password_mail(email)
            message = _('Reset password mail sent.')  #一个反馈信息
            status = True
        else:
            message = _('The email has not been registered')
            status = False
        return render_template('feedback.html', status=status, message=message)
    return render_template('forgot-password.html')

@home.route('/reset-password/<string:token>/', methods=['GET','POST'])
def reset_password(token):
    '''重设密码'''
    if current_user.is_authenticated():
        return redirect(request.args.get('next') or url_for('home.index'))
    if RT.query.get(token):
        return render_template('feedback.html', status=False, message=_('Token has been used'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        RT.add(token)
        try:
            email = ts.loads(token, salt="password-reset-key", max_age=86400)
        except:
            return render_template('feedback.html', status=False, message='Your token has expired.')
        user = User.query.filter_by(email=email).first_or_404()
        password = form['password'].data
        user.set_password(password)
        flash('Password Changed')
        return redirect(url_for('home.signin'))
    return render_template('reset-password.html',form=form)



@home.route('/search/')
def search():
    ''' 搜索 '''
    keyword = request.args.get('q')
    if not keyword:
        return redirect(url_for('home.index'))

    courses = Course.query.filter(Course.name.like('%' + keyword + '%')).join(CourseRate).order_by(Course.term.desc()).order_by(CourseRate.upvote_count.desc())
    try:
        page = int(request.args.get('page', 1))
    except:
        page = 1
    courses_paged = courses.paginate(page=page, per_page=10)
    if not courses:
        return 404
    else:
        return render_template('search.html', keyword=keyword, courses=courses_paged)


@home.route('/report-bug/')
def report_bug():
    ''' 报bug表单 '''

    return render_template('report-bug.html')


@home.route('/about/')
def about():
    '''关于我们,用来放一些联系方式'''

    return render_template('about.html')


@home.route('/test/')
def test():
    '''前端html页面效果测试专用'''

    return render_template('test.html')



