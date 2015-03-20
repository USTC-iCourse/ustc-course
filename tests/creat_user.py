import sys
sys.path.append('..')  # fix import directory


from app import app,db,user_datastore

user_datastore.create_user(email='test@163.com',password='password')
