from typing import List
import os
import re
from app.models import Course, CourseSearchCache, CourseRate, Review, ReviewSearchCache, CourseTerm, ReviewComment
from app.models.searchcache import is_chinese_stop_char
from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import or_
from sqlalchemy.orm import lazyload, load_only
import jieba
# from app.utils import print_sqlalchemy_statement


filter = lambda x: re.sub(r"""[~`!@#$%^&*{}\[\]\\:\";'<>,/\+\-\~\(\)><，、。：【】（）？“”「」·\x00-\x1F\x7F]""", " ", x)


def init() -> None:
    jieba.dt.tmp_dir = os.path.expanduser("~/.cache/jieba")
    os.makedirs(jieba.dt.tmp_dir, exist_ok=True)
    jieba.initialize()


# len >= 5 and only contains digits or letters
# it's possible that this match keywords like "python"
def is_course_id(x: str) -> bool:
    if len(x) >= 5:
        return x.isascii() and x.isalnum()
    return False


def search(keywords: List[str], page: int, per_page: int) -> Pagination:
    raw_keywords = [i.strip() for i in keywords if i.strip()]
    cid_keywords = []
    natural_keywords = []
    for keyword in raw_keywords:
        if is_course_id(keyword):
            cid_keywords.append(keyword.upper())
        else:
            natural_keywords.append(keyword)
    # handling course id (courseries)
    cid_query = None
    if cid_keywords:
        for cid in cid_keywords:
            query = Course.query.filter(CourseTerm.courseries.like(cid + "%")).filter(CourseTerm.course_id == Course.id)
            
            if cid_query is None:
                cid_query = query
            else:
                cid_query = cid_query.union(query)

    # use jieba to cut keywords
    natural_keywords = " ".join(
        # enforce keyword in search result
        ["+" + i.strip() for i in jieba.cut(" ".join(natural_keywords)) if i.strip() and not is_chinese_stop_char(i.strip())]
        + cid_keywords
    )

    results = CourseSearchCache.query.filter(CourseSearchCache.text.match(natural_keywords)).options(load_only(CourseSearchCache.id))
    ids = [result.id for result in results]
    results = Course.query.filter(Course.id.in_(ids))
    if cid_query is not None:
        if "+" in natural_keywords:
            results = results.intersect(cid_query)
        else:
            results = results.union(cid_query)

    if results.count() == 0:
        # fallback: search with every single char
        allchars = set()
        for word in keywords:
            for char in word:
                if not is_chinese_stop_char(char):
                    allchars.add("+" + char)
        allchars = " ".join(allchars)
        results = CourseSearchCache.query.filter(CourseSearchCache.text.match(allchars)).options(load_only(CourseSearchCache.id))
        ids = [result.id for result in results]
        results = Course.query.filter(Course.id.in_(ids))
    results = results.join(CourseRate).order_by(Course.QUERY_ORDER())
    # print_sqlalchemy_statement(results)
    results = results.paginate(page=page, per_page=per_page)

    return results


def search_reviews(
    keywords: List[str], page: int, per_page: int, current_user
) -> Pagination:
    # use jieba to cut keywords
    keywords = " ".join([i.strip() for i in jieba.cut(" ".join(keywords)) if i.strip()])
    match_expr = ReviewSearchCache.text.match(keywords)
    # Don't load comments and teachers -- avoid duplication in SQL response
    # some extra fields are loaded when being joined...
    results = Review.query.options(lazyload(Review.comments), lazyload(Review.course, Course.teachers))
    results = results.join(ReviewSearchCache).filter(match_expr)
    results = results.filter(Review.is_blocked == False).filter(Review.is_hidden == False)
    if not current_user.is_authenticated or current_user.identity != 'Student':
        if current_user.is_authenticated:
            results = results.filter(or_(Review.only_visible_to_student == False, Review.author == current_user.id))
        else:
            results = results.filter(Review.only_visible_to_student == False)
    results = results.order_by(match_expr.desc(), Review.update_time.desc())
    # print_sqlalchemy_statement(results)

    results = results.paginate(page=page, per_page=per_page)

    return results
