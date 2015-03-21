from app.models import Course

course = Course(cno='1111',name='diandonglixue')
course = course.save()
print(course.id)
