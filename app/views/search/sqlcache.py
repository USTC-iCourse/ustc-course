from typing import List, Tuple
from app.models import Course, CourseSearchCache, Review, ReviewSearchCache
from flask_sqlalchemy.pagination import Pagination
import jieba


def search(keywords: List[str], page: int, per_page: int) -> Tuple[List[Course], int]:
    # use jieba to cut keywords
    keywords = " ".join(jieba.cut(" ".join(keywords)))
    results = CourseSearchCache.query.filter(CourseSearchCache.text.match(keywords)).paginate(page=page, per_page=per_page)
    # CourseSearchCache -> Course
    results.items = [Course.query.get(result.id) for result in results.items]

    return results.items, results.total


def search_reviews(keywords: List[str], page: int, per_page: int, current_user) -> Pagination:
    # use jieba to cut keywords
    keywords = " ".join(jieba.cut(" ".join(keywords)))
    results = ReviewSearchCache.query.filter(ReviewSearchCache.text.match(keywords)).paginate(page=page, per_page=per_page)
    # ReviewSearchCache -> Review
    results.items = [Review.query.get(result.id) for result in results.items]

    return results
