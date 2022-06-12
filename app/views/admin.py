from flask import Blueprint,render_template,abort,redirect,url_for,request,abort
from app.models import Banner
from app.forms import BannerForm
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
    return render_template('banner-edit.html', form=BannerForm(), banner=banner, banner_history=banner_history, title='Banner 设置')

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
