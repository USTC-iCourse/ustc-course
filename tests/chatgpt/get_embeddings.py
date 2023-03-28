import sys
sys.path.append('../..')  # fix import directory

from app import app, db
from app.models import Review, ReviewComment

import openai
import os
import traceback
from markdownify import markdownify
import time

from milvus_connector import milvus_collection


if os.getenv("OPENAI_API_KEY"):
    openai.api_key = os.getenv("OPENAI_API_KEY")
else:
    raise ValueError('OPENAI_API_KEY environment variable is not set')

if os.getenv("HTTP_PROXY"):
    openai.proxy = os.getenv("HTTP_PROXY")
else:
    raise ValueError('HTTP_PROXY environment variable is not set')


def get_user(review):
    if review.is_anonymous:
        return '匿名用户'
    else:
        return '用户"' + review.author.username + '"'


def get_course(course):
    if len(course.teachers) == 0:
        return '《' + course.name + '》'
    else:
        teachers = sorted([ teacher.name for teacher in course.teachers ])
        return '、'.join(teachers) + '老师的《' + course.name + '》'


def get_course_term(review):
    if review.term_display == '未知':
        return ''
    else:
        return review.term_display + '季学期'


def get_embedding_of_content(content):
    embedding = openai.Embedding.create(input=content, model="text-embedding-ada-002")
    return (embedding["data"][0]["embedding"], embedding["usage"]["total_tokens"])


def generate_prompt(review):
    header = get_user(review) + '在' + get_course(review.course) + '课程' + get_course_term(review) + '的点评：\n'
    content = markdownify(review.content, strip=['a', 'img'])
    return header + content


def save_embedding(review, embedding):
    entities = [
        [review.id],
        [review.course_id],
        [review.author_id],
        [embedding]
    ]
    start_time = time.time()
    insert_result = milvus_collection.insert(entities)
    milvus_collection.flush()
    elapsed_time = time.time() - start_time
    print(f"Saved embedding to Milvus: num_documents {milvus_collection.num_entities}, time {elapsed_time}")


def get_embedding_of_review(review):
    prompt = generate_prompt(review)
    try:
        print(prompt)
        start_time = time.time()
        (embedding, tokens) = get_embedding_of_content(prompt)
        elapsed_time = time.time() - start_time

        prompt_length = len(prompt)
        print(f"Get embedding of review #{review.id}, course #{review.course_id}, author #{review.author_id}, length {prompt_length}, num_tokens {tokens}, time {elapsed_time}")

        save_embedding(review, embedding)
    except openai.error.APIConnectionError:
        raise
    except KeyboardInterrupt:
        raise
    except:
        traceback.print_exc()


def review_embedding_exists(review):
    query = 'id == ' + str(review.id)
    res = milvus_collection.query(expr=query, offset=0, limit=1, output_fields=['id'], consistency_level="Strong")
    if len(res) > 0:
        print(f"Skipped review #{review.id} because it already exists in Milvus")
        return True
    else:
        return False


def get_embedding_of_all_reviews():
    print('Querying all public reviews...')
    public_reviews = Review.query.filter(Review.is_hidden == False).filter(Review.is_blocked == False).filter(Review.only_visible_to_student == False).order_by(Review.id).all()
    print('Iterating over ' + str(len(public_reviews)) + ' public reviews...')
    for review in public_reviews:
        if not review_embedding_exists(review):
            get_embedding_of_review(review)


print("Start getting embeddings...")
get_embedding_of_all_reviews()
