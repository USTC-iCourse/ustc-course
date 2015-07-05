#!/usr/bin/env python3
import sys
sys.path.append('..')  # fix import directory

from app import app
from app.utils import send_confirm_mail
from app.models import User

# require an app context to work
ctx = app.test_request_context()
ctx.push()

users = User.query.filter(User.confirmed_at == None).all()
for user in users:
        if user.email == '':
                continue
        print(user.email)
        send_confirm_mail(user.email)

