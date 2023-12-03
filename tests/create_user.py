import sys
sys.path.append('..')  # fix import directory
from app.models import User
from app import app

with app.app_context():
    user = User('test','test@test.com','test')
    user.save()
    print('<User:test,test>')
    user.confirm()
