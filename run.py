from app import app
from app import db
from random import randint
from app.models import CourseReview, Course, Student, User

debug = True

def start():
    if debug:
        db.create_all()
    app.run(debug=debug,host='0.0.0.0',port=8080)



if __name__ == '__main__':
    start()
