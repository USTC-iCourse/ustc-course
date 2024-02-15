from typing import List
from app.models import Course, CourseSearchCache, CourseRate, Review, ReviewSearchCache, CourseTerm
from app.models.searchcache import is_chinese_stop_char
from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import or_
import jieba
import re


filter = lambda x: re.sub(r"""[~`!@#$%^&*{}\[\]\\:\";'<>,/\+\-\~\(\)><\x00-\x1F\x7F]""", " ", x)


def init() -> None:
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

    results = CourseSearchCache.query.filter(CourseSearchCache.text.match(natural_keywords))
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
        results = CourseSearchCache.query.filter(CourseSearchCache.text.match(allchars))
        ids = [result.id for result in results]
        results = Course.query.filter(Course.id.in_(ids))
    results = results.join(CourseRate).order_by(Course.QUERY_ORDER()).paginate(page=page, per_page=per_page)

    return results


def search_reviews(
    keywords: List[str], page: int, per_page: int, current_user
) -> Pagination:
    # use jieba to cut keywords
    keywords = " ".join([i.strip() for i in jieba.cut(" ".join(keywords)) if i.strip()])
    results = ReviewSearchCache.query.filter(ReviewSearchCache.text.match(keywords))
    results = results.filter(ReviewSearchCache.is_blocked == False).filter(ReviewSearchCache.is_hidden == False)
    if not current_user.is_authenticated or current_user.identity != 'Student':
        if current_user.is_authenticated:
            results = results.filter(or_(ReviewSearchCache.only_visible_to_student == False, ReviewSearchCache.author == current_user.id))
        else:
            results = results.filter(ReviewSearchCache.only_visible_to_student == False)
    results = results.paginate(page=page, per_page=per_page)
    # ReviewSearchCache -> Review
    ids = [result.id for result in results.items]
    results.items = Review.query.filter(Review.id.in_(ids)).all()

    return results
