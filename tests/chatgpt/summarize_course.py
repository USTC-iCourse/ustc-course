import sys
sys.path.append('../..')  # fix import directory

from app import app, db
from app.models import Review, Course, CourseRate

import sys
import os
import traceback
import time
import subprocess
from multiprocessing import Pool
from sqlalchemy.orm import sessionmaker
from app.views.ai.summarize_course import get_summary_of_course


if not app.config['OPENAI_API_KEY']:
    raise ValueError('OPENAI_API_KEY not found')


def handle_summarize_course(course_id):
    Session = sessionmaker(bind=db.engine)
    session = Session()
    course = session.query(Course).filter_by(id=course_id).first()
    if course.summary_update_time:
        non_summarized_reviews = session.query(Review).filter_by(course_id=course_id).filter(Review.update_time >= course.summary_update_time).count()
    else:
        non_summarized_reviews = session.query(Review).filter_by(course_id=course_id).count()

    if not course.summary or non_summarized_reviews > 0:
        print("Summarizing course:", course, flush=True)
        summary = get_summary_of_course(course)
        if summary:
            course.summary = summary
            course.summary_update_time = datetime.utcnow()
            session.commit()
            session.flush()


def invoke_summarize_course(course_id):
    subprocess.run(["python3", sys.argv[0], str(course_id)])


def get_summary_of_all_courses():
    print('Summarizing all courses...')
    courses = Course.query.join(CourseRate).filter(Course.id == CourseRate.id).order_by(CourseRate.review_count.desc()).filter(CourseRate.review_count > 0).all()
    print('Iterating over ' + str(len(courses)) + ' courses...')
    all_course_ids = [course.id for course in courses]
    with Pool(processes=16) as p:
        p.map(invoke_summarize_course, all_course_ids)


if len(sys.argv) == 2 and sys.argv[1]:
    with app.app_context():
        handle_summarize_course(int(sys.argv[1]))
else:
    print("Start summarizing reviews of all courses...")
    with app.app_context():
        get_summary_of_all_courses()
