from flask import Blueprint,render_template,abort,redirect,url_for,request,abort,jsonify
from app.models import Banner, Announcement
from app.forms import BannerForm, AnnouncementForm
from flask_security import current_user,login_required

admin = Blueprint('admin',__name__)

@admin.before_request
@login_required
def restrict_to_admins():
    if not current_user.is_admin:
        abort(404)

@admin.route('/admin/set-banner/')
@login_required
def set_banner():
    banner = Banner.query.order_by(Banner.publish_time.desc()).first()
    banner_history = Banner.query.order_by(Banner.publish_time.desc()).all()
    return render_template('admin/edit-banner.html', form=BannerForm(), banner=banner, banner_history=banner_history, title='Banner 设置')

@admin.route('/admin/set-banner-post/', methods=['POST'])
@login_required
def set_banner_post():
    banner = Banner()
    banner_form = BannerForm(formdata=request.form, obj=banner)
    if banner_form.validate_on_submit():
        banner_form.populate_obj(banner)
        banner.add()
        return redirect(url_for('admin.set_banner'))
    abort(500)

@admin.route('/admin/add-announcement/')
@login_required
def add_announcement():
    return render_template('admin/add-announcement.html', form=AnnouncementForm(), title='发布公告')

@admin.route('/admin/add-announcement-post/', methods=['POST'])
@login_required
def add_announcement_post():
    announcement = Announcement()
    form = AnnouncementForm(formdata=request.form, obj=announcement)
    if form.validate_on_submit():
        form.populate_obj(announcement)
        announcement.author = current_user
        announcement.last_editor = current_user
        announcement.add()
        return redirect(url_for('home.announcements'))
    abort(500)

@admin.route('/admin/edit-announcement/<int:announcement_id>')
@login_required
def edit_announcement(announcement_id):
    announcements = Announcement.query.filter(Announcement.id == announcement_id).all()
    if len(announcements) != 1:
        abort(404)
    announcement = announcements[0]
    return render_template('admin/edit-announcement.html', form=AnnouncementForm(), announcement=announcement, title='编辑公告')

@admin.route('/admin/edit-announcement-post/<int:announcement_id>', methods=['POST'])
@login_required
def edit_announcement_post(announcement_id):
    announcements = Announcement.query.filter(Announcement.id == announcement_id).all()
    if len(announcements) != 1:
        abort(404)
    announcement = announcements[0]
    form = AnnouncementForm(formdata=request.form, obj=announcement)
    if form.validate_on_submit():
        form.populate_obj(announcement)
        announcement.last_editor = current_user
        announcement.save()
        return redirect(url_for('home.announcements'))
    abort(500)

@admin.route('/admin/delete-announcement/', methods=['POST'])
@login_required
def delete_announcement():
    announcement_id = request.values.get('announcement_id')
    if not announcement_id:
        return jsonify(ok=False, message='Bad request')
    announcements = Announcement.query.filter(Announcement.id == announcement_id).all()
    if len(announcements) != 1:
        return jsonify(ok=False, message='Announcement Not Found')
    announcement = announcements[0]
    announcement.delete()
    return jsonify(ok=True)
