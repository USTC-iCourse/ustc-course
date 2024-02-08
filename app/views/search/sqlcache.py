from typing import List
from app.models import Course, CourseSearchCache, Review, ReviewSearchCache
from flask_sqlalchemy.pagination import Pagination
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
    results = ReviewSearchCache.query.filter(
        ReviewSearchCache.text.match(keywords)
    ).paginate(page=page, per_page=per_page)
    # ReviewSearchCache -> Review
    ids = [result.id for result in results.items]
    results.items = Review.query.filter(Review.id.in_(ids)).all()

    return results
