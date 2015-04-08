from app import app
from app import db
from random import randint
from app.models import CourseReview, Course, Student, User

debug = True

def start():
    if debug:
        db.drop_all()
        init_db()
    app.run(debug=debug,host='0.0.0.0',port=8080)


def init_db():
    db.create_all()
    for i in range(1, 100):
        Student.create(sno='PB10' + str(randint(100000, 999999)), name='李博杰', dept= '11')
        course = Course.create(cno='test'+str(randint(100000,999999)),term='20142',name='线性代数',dept='test')

    CourseReview.create(author_id=1, course_id=1, rate=4, upvote=2, content='Hello World')
    CourseReview.create(author_id=2, course_id=1, rate=4, upvote=2, content='Hello World1')
    CourseReview.create(author_id=3, course_id=1, rate=4, upvote=2, content='Hello World2')
    CourseReview.create(author_id=4, course_id=1, rate=4, upvote=2, content='Hello World3')
    CourseReview.create(author_id=5, course_id=1, rate=4, upvote=2, content='Hello World4')
    CourseReview.create(author_id=6, course_id=1, rate=4, upvote=2, content='Hello World5')

    try:
        user = User(username='test', email='test@163.com',password='test')
        user.confirm()
        print(user)
    except:
        pass


if __name__ == '__main__':
    start()
