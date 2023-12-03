import sys
sys.path.append('../..')  # fix import directory

from app import app, db
from app.models import Review, Course, CourseRate

from openai_helper import openai
from prompt_generator import generate_summary_prompt, SUMMARY_EXPECTED_LENGTH

import os
import traceback
import time


def get_chatgpt_completion(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            { "role": "user", "content": prompt }
        ]
        )
    return (response["choices"][0]["message"]["content"],
            response["usage"]["prompt_tokens"],
            response["usage"]["completion_tokens"])


def get_chatgpt_summary(course, prompt):
    try:
        start_time = time.time()
        (completion, prompt_tokens, completion_tokens) = get_chatgpt_completion(prompt)
        elapsed_time = time.time() - start_time

        prompt_length = len(prompt)
        print(f"Get summary of course #{course.id}, prompt_length {prompt_length}, prompt_tokens {prompt_tokens}, completion_tokens {completion_tokens}, time {elapsed_time}:")
        print(completion)
        return completion
    except openai.error.APIConnectionError:
        raise
    except KeyboardInterrupt:
        raise
    except:
        traceback.print_exc()


def get_summary_of_course(course):
    public_reviews = (Review.query.filter_by(course_id=course.id)
        .filter(Review.is_hidden == False).filter(Review.is_blocked == False).filter(Review.only_visible_to_student == False)
        .order_by(Review.upvote_count.desc(), Review.publish_time.desc())
        .all()
        )
    if len(public_reviews) == 0:
        return None
    prompt = generate_summary_prompt(public_reviews)
    if len(prompt) <= SUMMARY_EXPECTED_LENGTH:  # too short, no need to summarize
        return prompt
    else:
        return get_chatgpt_summary(course, prompt)


def get_summary_of_all_courses():
    print('Summarizing all courses...')
    courses = Course.query.join(CourseRate).filter(Course.id == CourseRate.id).order_by(CourseRate.review_count.desc()).filter(CourseRate.review_count > 0).all()
    print('Iterating over ' + str(len(courses)) + ' courses...')
    for course in courses:
        if not course.summary:
            course.summary = get_summary_of_course(course)
            db.session.commit()


print("Start summarizing reviews of all courses...")
with app.app_context():
    get_summary_of_all_courses()
