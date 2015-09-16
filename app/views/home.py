from flask import Blueprint,request, redirect,url_for,render_template,flash, abort, jsonify
from flask.ext.login import login_user, login_required, current_user, logout_user
from app.models import User, RevokedToken as RT, Course, CourseRate, Teacher, Review
from app.forms import LoginForm, RegisterForm, ForgotPasswordForm, ResetPasswordForm
from app.utils import ts, send_confirm_mail, send_reset_password_mail
from flask.ext.babel import gettext as _
from datetime import datetime
from sqlalchemy import union, or_
from .course import termlist, deptlist, QUERY_ORDER

home = Blueprint('home',__name__)

@home.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    reviews_paged = Review.query.order_by(Review.id.desc()).paginate(page=page, per_page=per_page)
    return render_template('index.html', reviews=reviews_paged)

@home.route('/signin/',methods=['POST','GET'])
def signin():
    next_url = request.args.get('next') or url_for('home.index')
    if current_user.is_authenticated():
        return redirect(next_url)
    form = LoginForm()
    error = ''
    if form.validate_on_submit():
        user, status, confirmed = User.authenticate(form['username'].data,form['password'].data)
        remember = form['remember'].data
        if user:
            if status:
                #validate uesr
                login_user(user, remember=remember)
                if request.args.get('ajax'):
                    return jsonify(status=200, next=next_url)
                else:
                    return redirect(next_url)
            elif not confirmed:
                '''没有确认邮箱的用户'''
                message = '请点击邮箱里的激活链接。 <a href=%s>重发激活邮件</a>'%url_for('.confirm_email',
                    email=user.email,
                    action='send')
                if request.args.get('ajax'):
                    return jsonify(status=403, msg=message)
                else:
                    return render_template('feedback.html', status=False, message=message)
            else:
                error = _('用户名或密码错误！')
        else:
            error = _('用户名或密码错误！')
    #TODO: log the form errors
    if request.args.get('ajax'):
        return jsonify(status=404, msg=error)
    else:
        return render_template('signin.html',form=form, error=error)

@home.route('/su/<int:user_id>')
@login_required
def switch_user(user_id):
    if not current_user.is_admin:
        abort(403)
    user = User.query.get(user_id)
    if not user:
        abort(404)
    logout_user()
    login_user(user)
    return redirect(url_for('home.index'))


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
        return render_template('feedback.html', status=True, message=_('我们已经向您发送了激活邮件，请在邮箱中点击激活链接。如果您没有收到邮件，有可能是在垃圾箱中。'))
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
            return render_template('feedback.html', status=False, message=_('此激活链接无效，请准确复制邮件中的链接。'))
        if RT.query.get(token):
            return render_template('feedback.html', status=False, message=_('此激活链接已被使用过。'))
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
        return render_template('feedback.html', status=True, message=_('邮件已经发送，请查收！'))
    else:
        abort(404)


@home.route('/logout/')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home.index'))

@home.route('/change-password/', methods=['GET'])
def change_password():
    '''在控制面板里发邮件修改密码，另一个修改密码在user.py里面'''
    if not current_user.is_authenticated():
        return redirect(url_for('home.signin'))
    send_reset_password_mail(current_user.email)
    return render_template('feedback.html', status=True, message=_('密码重置邮件已经发送。'))


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
            message = _('密码重置邮件已发送。')  #一个反馈信息
            status = True
        else:
            message = _('此邮件地址尚未被注册。')
            status = False
        return render_template('feedback.html', status=status, message=message)
    return render_template('forgot-password.html')

@home.route('/reset-password/<string:token>/', methods=['GET','POST'])
def reset_password(token):
    '''重设密码'''
    if RT.query.get(token):
        return render_template('feedback.html', status=False, message=_('此密码重置链接已被使用过。'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        RT.add(token)
        try:
            email = ts.loads(token, salt="password-reset-key", max_age=86400)
        except:
            return render_template('feedback.html', status=False, message=_('此密码重置链接无效，请准确复制邮件中的链接。'))
        user = User.query.filter_by(email=email).first_or_404()
        password = form['password'].data
        user.set_password(password)
        logout_user()
        flash('密码已经修改，请使用新密码登录。')
        return redirect(url_for('home.signin'))
    return render_template('reset-password.html',form=form)



@home.route('/search/')
def search():
    ''' 搜索 '''
    keyword = request.args.get('q')
    if not keyword:
        return redirect(url_for('home.index'))

    term = request.args.get('term',None,type=str)
    course_type = request.args.get('type',None,type=int)
    department = request.args.get('dept',None,type=int)
    campus = request.args.get('campus',None,type=str)
    course_query = Course.query
    if term:
        # 学期
        course_query = course_query.filter(Course.term==term)
    if course_type:
        # 课程类型
        course_query = course_query.filter(Course.course_type==course_type)
    if department:
        # 开课院系
        course_query = course_query.filter(Course.dept_id==department)
    if campus:
        # 开课地点
        course_query = course_query.filter(Course.campus==campus)

    def ordering(query_obj):
        return query_obj.join(CourseRate).order_by(*QUERY_ORDER).subquery().select()
    def match_courses(filter):
        return ordering(course_query.filter(filter))

    teacher_match = ordering(course_query.join(Course.teachers).filter(Teacher.name == keyword))
    exact_match = match_courses(Course.name == keyword)
    fuzzy_keyword = keyword.replace(' ', '').replace('%', '')
    include_match = match_courses(Course.name.like('%' + fuzzy_keyword + '%'))
    fuzzy_match = match_courses(Course.name.like('%' + '%'.join([ char for char in fuzzy_keyword ]) + '%'))

    courses = Course.query.select_entity_from(union(teacher_match, exact_match, include_match, fuzzy_match))
    if not courses:
        abort(404)

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    courses_paged = courses.paginate(page=page, per_page=per_page)

    return render_template('search.html', keyword=keyword, courses=courses_paged,
            dept=department, term=term,
            deptlist=deptlist, termlist=termlist, this_module='home.search')



@home.route('/about/')
def about():
    '''关于我们，网站介绍、联系方式'''

    return render_template('about.html')


@home.route('/community-rules/')
def community_rules():
    '''社区规范页面'''

    return render_template('community-rules.html')


@home.route('/report-bug/')
def report_bug():
    ''' 报bug表单 '''

    return render_template('report-bug.html')


@home.route('/not_found/')
def not_found():
    '''返回404页面'''
    return render_template('404.html')


@home.route('/songshu/')
def songshu():
    '''Test'''

    return render_template('songshu.html')
