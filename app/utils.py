from itsdangerous import URLSafeTimedSerializer
from flask_mail import Mail,Message
from . import app
from flask import render_template, url_for
from random import randint
from datetime import datetime
from app.models import ImageStore
import hashlib
import os


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

    msg = Message(subject=subject, html=html, sender='test@ibat.me', recipients=[email])
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


