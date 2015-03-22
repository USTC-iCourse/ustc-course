"""
    ustc courses

    :copyright: (c) 2015 by the USTC-Courses Team.

"""

import os
from flask import Flask,request
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.security import Security,  SQLAlchemyUserDatastore


app = Flask(__name__)
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
    #TODO: config file
    #app.config.from_object('config')

#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////'+os.path.join(app.root_path, 'test.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
#app.config['SECURITY_PASSWORD_HASH'] = bcrypt
db = SQLAlchemy(app)




from app.views import course
from app.views import home,review
#from app.models import User,Role
from app.views import api
app.register_blueprint(home,url_prefix='')
app.register_blueprint(course,url_prefix='/course')
app.register_blueprint(review, url_prefix='/review')
app.register_blueprint(api, url_prefix='/api')

# Setup Flask-Security
#user_datastore = SQLAlchemyUserDatastore(db, User, Role)
#security = Security(app, user_datastore)
