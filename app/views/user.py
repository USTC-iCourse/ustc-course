from flask import Blueprint,render_template,abort,redirect,url_for,request
from app.models import User
from app.forms import LoginForm
from app.ext.login import login_uesr


user = Blueprint('user', __name__)



