from itsdangerous import URLSafeTimedSerializer
from flask_mail import Mail,Message
from . import app
from flask import render_template, url_for, Markup
from random import randint
from datetime import datetime
from app.models import ImageStore, User
import hashlib
import os
from lxml.html.clean import Cleaner
import pytz
import re


mail = Mail(app)
ts = URLSafeTimedSerializer(app.config["SECRET_KEY"])


def rand_str():
    random_num = randint(100000,999999)
    raw_str = str(datetime.utcnow()) + str(randint(100000,999999))
    hash_fac = hashlib.new('ripemd160')
    hash_fac.update(raw_str.encode('utf-8'))
    return hash_fac.hexdigest()


def send_confirm_mail(email):
    subject = 'Confirm your email.'
    token = ts.dumps(email, salt='email-confirm-key')

    confirm_url = url_for(
        'home.confirm_email',
        action='confirm',
        token=token,
        _external=True)
    html = render_template('email/activate.html',
            confirm_url = confirm_url)

    msg = Message(subject=subject, html=html, recipients=[email])
    mail.send(msg)

def send_reset_password_mail(email):
    subject = 'Reset your password'
    token = ts.dumps(email, salt='password-reset-key')

    reset_url = url_for(
        'home.reset_password',
        token=token,
        _external=True)
    html = render_template('email/reset-password.html',
            reset_url = reset_url)

    msg = Message(subject=subject, html=html, recipients=[email])
    mail.send(msg)



def allowed_file(filename,type):
    return '.' in filename and \
            filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS'][type]

def handle_upload(file,type):
    ''' type is the file type,for example:image.
    more file type to be added in the future.'''
    if file and allowed_file(file.filename,type):
        old_filename = file.filename
        file_suffix = old_filename.split('.')[-1]
        new_filename = rand_str() + '.' + file_suffix
        try:
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'],type+'s/')
            file.save(os.path.join(upload_path, new_filename))
        except FileNotFoundError:
            os.makedirs(upload_path)
            file.save(os.path.join(upload_path, new_filename))
        except Exception as e:
            return False,e
        img = ImageStore(old_filename,new_filename)
        img.save()
        return True,new_filename
    return False,"File type disallowd!"


def sanitize(text):
    if text.strip():
        cleaner = Cleaner(safe_attrs_only=False)
        return cleaner.clean_html(text)
    else:
        return text

@app.template_filter('abstract')
def html_abstract(text):
    return Markup(text).striptags()[0:150]

def editor_parse_at(text):
    if not text.endswith('\n'):
        text = text + '\n' # the parse function will not work with @somebody
    matches = re.findall('@[^@&<>"\':;?+=,\s]+', text)
    if not matches:
        return text
    for match in matches:
        username = match[1:]
        if len(username) > 30:
            continue
        if validate_username(username, check_db=False) == 'OK':
            user = User.query.filter_by(username=username).first()
            if user:
                url = url_for('user.view_profile', user_id=user.id)
                # replace @ to Unicode char ＠ to avoid further substitution when review is edited
                atstring = '<a href="' + url + '">' + '＠' + username + '</a>'
                # warn: simple str.replace is wrong.
                # consider the following case: @boj @bojjenny42
                #   @boj is first matched and replaced, then the string becomes <a href="">@boj</a> <a href="">@boj</a>jenny42
                # the following regexp would do the trick.
                text = re.sub("@" + re.escape(username) + '([@&<>"\':;?+=,\s])',
                              '<a href="' + url + '">' + '＠' + re.escape(username) + '</a>' + '\\1', text)
    return text

@app.template_filter('localtime')
def localtime_minute(date):
    local = pytz.utc.localize(date, is_dst=False).astimezone(pytz.timezone('Asia/Shanghai'))
    return local.strftime('%Y-%m-%d %H:%M')


RESERVED_USERNAME = set(['管理员', 'admin', 'root',
    'Administrator', 'example', 'test'])

def validate_username(username, check_db=True):
    if re.search('[@&<>"\':;?+=,\s]', username):
        return ('此用户名含有非法字符，不能注册！')
    if re.match('[a-zA-Z0-9-]+\.[a-zA-Z]+$', username):
        return ('此用户名看起来像域名，不能注册！')
    if username in RESERVED_USERNAME:
        return ('此用户名已被保留，不能注册！')
    if check_db and User.query.filter_by(username=username).first():
        return ('此用户名已被他人使用！')
    return 'OK'

def validate_email(email):
    regex = re.compile("[a-zA-Z0-9_]+@(mail\.)?ustc\.edu\.cn")
    if not regex.fullmatch(email):
        return ('必须使用科大邮箱注册!')
    if User.query.filter_by(email=email).first():
        return ('此邮件地址已被注册！')
    return 'OK'
