from flask import Blueprint,render_template,abort,redirect,url_for,request,abort
from app.models import Course
from flask.login import current_user,

admin = Blueprint('admin',__name__)

@admin.before_request
def restrict_to_admins():
    if not current_users.is_admin():
        return "You have no rignt to do this"
