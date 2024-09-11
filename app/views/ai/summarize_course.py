import sys
from app import app, db
from app.models import Review, Course, CourseRate

from openai import OpenAI
from app.views.ai.prompt_generator import generate_summary_prompt, SUMMARY_EXPECTED_LENGTH

import sys
import os
import traceback
import time
import subprocess
from multiprocessing import Pool
from sqlalchemy.orm import sessionmaker


def get_chatgpt_completion(system_prompt, user_prompt):
    if 'OPENAI_BASE_URL' in app.config:
        client = OpenAI(
            base_url=app.config['OPENAI_BASE_URL'],
            api_key=app.config['OPENAI_API_KEY'],
        )
    else:
        client = OpenAI(
            api_key=app.config['OPENAI_API_KEY'],
        )
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            { "role": "system", "content": system_prompt },
            { "role": "user", "content": user_prompt },
        ]
    )
    return response.choices[0].message.content, response.usage.prompt_tokens, response.usage.completion_tokens


def get_chatgpt_summary(course, system_prompt, user_prompt, expected_summary_length):
    try:
        start_time = time.time()
        completion, prompt_tokens, completion_tokens = get_chatgpt_completion(system_prompt, user_prompt)
        elapsed_time = time.time() - start_time

        prompt_length = len(user_prompt)
        response_length = len(completion)
        print(f"Get summary of course #{course.id} {str(course)}: prompt_length {prompt_length}, response_length {response_length}, prompt_tokens {prompt_tokens}, completion_tokens {completion_tokens}, expected summary length {expected_summary_length}, time {elapsed_time}:", flush=True)
        print(completion, flush=True)
        return completion
    except KeyboardInterrupt:
        raise
    except:
        traceback.print_exc()
        print(flush=True)
        return None


def get_expected_summary_length(reviews):
    if len(reviews) == 0:
        return None
    total_length = 0
    for review in reviews:
        total_length += len(review.content)
    if len(reviews) < 5 and total_length < 3000:
        return None
    elif total_length < 2000:
        return 200
    elif total_length < 5000:
        return round(total_length / 10)
    else:
        return 500


def get_public_reviews(course):
    public_reviews = (Review.query.filter_by(course_id=course.id)
        .filter(Review.is_hidden == False).filter(Review.is_blocked == False).filter(Review.only_visible_to_student == False)
        .order_by(Review.upvote_count.desc(), Review.publish_time.desc())
        .all()
        )
    return public_reviews


def check_course_need_summary(course):
    public_reviews = get_public_reviews(course)
    return get_expected_summary_length(public_reviews) is not None


# return Tuple[bool, str | None]):
# bool: whether or not a summary is needed
# str | None: the summary. If generation failed, return None
def get_summary_of_course(course):
    public_reviews = get_public_reviews(course)
    expected_summary_length = get_expected_summary_length(public_reviews)
    if expected_summary_length:
        system_prompt, user_prompt = generate_summary_prompt(public_reviews, expected_summary_length)
        retry = 2
        for i in range(retry):
            summary = get_chatgpt_summary(course, system_prompt, user_prompt, expected_summary_length)
            if summary:
                return True, summary
        # failed to generate summary
        return True, None
    else:
        return False, None

