from itsdangerous import URLSafeTimedSerializer
from flask_mail import Mail,Message
from . import app
from flask import render_template, url_for


mail = Mail(app)
ts = URLSafeTimedSerializer(app.config["SECRET_KEY"])



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

    msg = Message(subject=subject, html=html, sender='test@ibat.me', recipients=[email])
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




