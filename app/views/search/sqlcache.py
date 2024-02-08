from typing import List
from app.models import Course, CourseSearchCache, Review, ReviewSearchCache
from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import or_
import jieba
import re


filter = lambda x: re.sub(r"""[~`!@#$%^&*{}\[\]\\:\";'<>,/\+\-\~\(\)><]""", " ", x)


def search(keywords: List[str], page: int, per_page: int) -> Pagination:
    # use jieba to cut keywords
    keywords = " ".join(
        # enforce keyword in search result
        ["+" + i.strip() for i in jieba.cut(" ".join(keywords)) if i.strip()]
    )
    results = CourseSearchCache.query.filter(
        CourseSearchCache.text.match(keywords)
    ).paginate(page=page, per_page=per_page)
    # CourseSearchCache -> Course
    ids = [result.id for result in results.items]
    results.items = Course.query.filter(Course.id.in_(ids)).all()

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
