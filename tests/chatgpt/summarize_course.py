import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.append(project_root)

from app import app, db
from app.models import Review, Course, CourseRate
from datetime import datetime

import traceback
import time
import subprocess
from multiprocessing import Pool
from sqlalchemy.orm import sessionmaker
from app.views.ai.summarize_course import get_summary_of_course, check_course_need_summary


if not app.config['OPENAI_API_KEY']:
    raise ValueError('OPENAI_API_KEY not found')


def handle_summarize_course(course_id):
    Session = sessionmaker(bind=db.engine)
    session = Session()
    course = session.query(Course).filter_by(id=course_id).first()
    print("Summarizing course:", course, flush=True)
    need_summary, summary = get_summary_of_course(course)
    if not need_summary:
        course.summary = None
        session.commit()
    # if a summary is needed but generation failed, do not update the database
    if need_summary and summary:
        course.summary = summary
        course.summary_update_time = datetime.utcnow()
        session.commit()


def invoke_summarize_course(course_id):
    subprocess.run(["python3", sys.argv[0], str(course_id)])


def get_summary_of_all_courses():
    print('Summarizing all courses...')
    courses = Course.query.join(CourseRate).filter(Course.id == CourseRate.id).order_by(CourseRate.review_count.desc()).filter(CourseRate.review_count > 0).all()
    print(f'Iterating over {len(courses)} courses...')
    course_ids_to_summarize = []
    for course in courses:
        if course.summary_update_time:
            non_summarized_reviews = Review.query.filter_by(course_id=course.id).filter(Review.update_time >= course.summary_update_time).count()
        else:
            non_summarized_reviews = 1

        if not course.summary or non_summarized_reviews > 0:
            if check_course_need_summary(course):
                course_ids_to_summarize.append(course.id)

    print(f'Found {len(course_ids_to_summarize)} courses to summarize')
    with Pool(processes=16) as p:
        p.map(invoke_summarize_course, course_ids_to_summarize)


if len(sys.argv) == 2 and sys.argv[1]:
    with app.app_context():
        handle_summarize_course(int(sys.argv[1]))
else:
    print("Start summarizing reviews of all courses...")
    with app.app_context():
        get_summary_of_all_courses()
