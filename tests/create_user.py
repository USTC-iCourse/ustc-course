import sys
sys.path.append('..')  # fix import directory
from app.models import User


user = User('test','test@test.com','test')
user.save()
print('<User:test,test>')
user.confirm()
