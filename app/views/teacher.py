from flask import Blueprint,render_template,abort,redirect,url_for,request, abort, flash
from app.models import *
from app.forms import TeacherProfileForm
from flask_login import login_user, current_user, login_required
from app.utils import handle_upload, sanitize
from flask_babel import gettext as _
import re

teacher = Blueprint('teacher', __name__)

def to_int(data):
    if data is None:
        return 0
    else:
        return int(data)

@teacher.route('/<int:teacher_id>')
@teacher.route('/<int:teacher_id>/')
def view_profile(teacher_id):
    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        abort(404)
    teacher.access_count += 1
    teacher.save_without_edit()

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10000, type=int)
    courses = teacher.courses.join(CourseRate).order_by(Course.QUERY_ORDER())
    courses_paged = courses.paginate(page=page, per_page=per_page)

    all_courses = courses.all()
    total_rating = sum([ to_int(course.course_rate._rate_total) for course in all_courses ])
    stats = {}
    stats['num_rating'] = sum([ to_int(course.course_rate.review_count) for course in all_courses ])
    if stats['num_rating'] == 0:
        stats['avg_rating'] = 0
    else:
        stats['avg_rating'] = total_rating * 1.0 / stats['num_rating']
    if len(all_courses) == 0:
        stats['normalized_rating'] = 0
    else:
        stats['normalized_rating'] = all_courses[0].compute_normalized_rate(total_rating, stats['num_rating'])

    return render_template('teacher-profile.html', teacher=teacher, courses=courses_paged, title=teacher.name, stats=stats,
                           description=teacher.name + '共有 ' + str(courses_paged.total) + ' 门课程，' + str(stats['num_rating']) + ' 个点评，平均分 ' + ('%.2f' % stats['avg_rating']))

@teacher.route('/<int:teacher_id>/profile_history/', methods=['GET'])
@login_required
def profile_history(teacher_id):
    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        abort(404)
    if not current_user.is_admin and teacher.info_locked:
        abort(403)
    return render_template('teacher-profile-history.html', teacher=teacher, title='教师信息编辑历史 - ' + teacher.name)

@teacher.route('/<int:teacher_id>/delete_image/', methods=['GET','POST'])
@login_required
def delete_image(teacher_id):
    teacher = Teacher.query.get(teacher_id)
    if current_user.is_blocked_now:
        abort(403)
    if not teacher:
        abort(404)
    if teacher.image_locked:
        abort(403)

    teacher.set_image(None)
    teacher.save()

    info_history = TeacherInfoHistory()
    info_history.save(teacher, current_user)
    return redirect(url_for('teacher.view_profile', teacher_id=teacher.id))

@teacher.route('/<int:teacher_id>/edit_profile/', methods=['GET','POST'])
@login_required
def edit_profile(teacher_id):
    teacher = Teacher.query.get(teacher_id)
    form = TeacherProfileForm(formdata=request.form, obj=teacher)
    errors = []
    if current_user.is_blocked_now:
        abort(403)
    if teacher.info_locked:
        errors.append(_("Teacher info is locked, please contact administrator to unlock"))
    elif form.validate_on_submit():
        #teacher.gender = form['gender'].data
        # 处理多个主页URL，每行一个
        homepage_data = form['homepage'].data.strip()
        if homepage_data:
            # 分割成多行并处理每个URL
            homepages = []
            invalid_urls = []
            # URL验证的正则表达式
            url_pattern = re.compile(
                r'^https?://'  # http:// 或 https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # 域名
                r'localhost|'  # localhost
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP地址
                r'(?::\d+)?'  # 可选的端口
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
            
            for line_num, line in enumerate(homepage_data.split('\n'), 1):
                homepage = line.strip()
                if homepage:  # 忽略空行
                    # 检查URL中是否包含空格（可能是多个URL写在同一行）
                    if ' ' in homepage or '\t' in homepage:
                        invalid_urls.append(f"第{line_num}行包含空白字符，可能包含多个URL或格式错误：{homepage}")
                        continue
                    
                    # 为没有协议的URL添加http://
                    if not homepage.startswith(('http://', 'https://')):
                        homepage = 'http://' + homepage
                    
                    # 使用正则表达式验证URL格式
                    if not url_pattern.match(homepage):
                        invalid_urls.append(f"第{line_num}行URL格式无效：{homepage}")
                        continue
                    
                    # 检查URL长度（避免过长的URL）
                    if len(homepage) > 500:
                        invalid_urls.append(f"第{line_num}行URL过长（超过500字符）：{homepage[:50]}...")
                        continue
                    
                    homepages.append(homepage)
            
            # 如果有无效的URL，显示错误
            if invalid_urls:
                errors.extend(invalid_urls)
                return render_template('teacher-settings.html', teacher=teacher, errors=errors, form=form, title='编辑教师信息 - ' + teacher.name)
            
            # 用换行符连接所有主页URL存储
            teacher.homepage = '\n'.join(homepages) if homepages else ''
        else:
            teacher.homepage = ''
        teacher.research_interest = form['research_interest'].data.strip()
        if request.files.get('avatar'):
            if teacher.image_locked:
                errors.append(_("Teacher photo is locked, please contact administrator to unlock"))
            else:
                avatar = request.files['avatar']
                ok,info = handle_upload(avatar,'image')
                if ok:
                    teacher.set_image(info)
                else:
                    errors.append(_("Avatar upload failed"))
        teacher.save()

        info_history = TeacherInfoHistory()
        info_history.save(teacher, current_user) 

        return redirect(url_for('teacher.view_profile', teacher_id=teacher.id))
    elif request.method == 'POST':
        errors = ['表单验证错误：' + str(form.errors)]
    return render_template('teacher-settings.html', teacher=teacher, errors=errors, form=form, title='编辑教师信息 - ' + teacher.name)

def save_teacher_and_render_template(teacher):
    teacher.save()
    form = TeacherProfileForm(formdata=request.form, obj=teacher)
    errors = []
    return render_template('teacher-settings.html', teacher=teacher, errors=errors, form=form, title='编辑教师信息 - ' + teacher.name)

@teacher.route('/<int:teacher_id>/lock_profile/', methods=['GET','POST'])
@login_required
def lock_profile(teacher_id):
    if not current_user.is_admin:
        abort(403)
    teacher = Teacher.query.get(teacher_id)
    teacher.info_locked = True
    return save_teacher_and_render_template(teacher)

@teacher.route('/<int:teacher_id>/unlock_profile/', methods=['GET','POST'])
@login_required
def unlock_profile(teacher_id):
    if not current_user.is_admin:
        abort(403)
    teacher = Teacher.query.get(teacher_id)
    teacher.info_locked = False
    return save_teacher_and_render_template(teacher)

@teacher.route('/<int:teacher_id>/lock_avatar/', methods=['GET','POST'])
@login_required
def lock_avatar(teacher_id):
    if not current_user.is_admin:
        abort(403)
    teacher = Teacher.query.get(teacher_id)
    teacher.image_locked = True
    return save_teacher_and_render_template(teacher)

@teacher.route('/<int:teacher_id>/unlock_avatar/', methods=['GET','POST'])
@login_required
def unlock_avatar(teacher_id):
    if not current_user.is_admin:
        abort(403)
    teacher = Teacher.query.get(teacher_id)
    teacher.image_locked = False
    return save_teacher_and_render_template(teacher)

