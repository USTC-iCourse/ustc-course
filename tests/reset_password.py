#!/usr/bin/python3
import sys
sys.path.append('..')
from app.models import User
import secrets

def reset_random_password(email):
    user = User.query.filter_by(email=email).first()
    if not user:
        print('User not found')
        return
    confirm = input('You are going to reset password for user ' + email + ' [y/N]')
    if confirm not in ('Y', 'y'):
        return
    password = secrets.token_hex(20)
    user.set_password(password)
    print('Password of user ' + email + ' is reset to ' + password)

email = sys.argv[1]
reset_random_password(email)
