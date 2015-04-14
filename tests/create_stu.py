import sys
sys.path.append('..')  # fix import directory

from app import app,db
from app.models import Student,Course
from random import randint, randrange

for i in range(10):
    Student.create('PB'+str(randint(100000,999999)),'用户'+str(randrange(100)),str(randrange(20)))

