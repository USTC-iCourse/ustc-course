from .sqllike import search as sqllike_search, search_reviews as sqllike_search_reviews
from .sqlcache import search as sqlcache_search, search_reviews as sqlcache_search_reviews
from flask_sqlalchemy.pagination import Pagination
from .pagination import MyPagination
from typing import List, Union
from app import app


backend = app.config.get("SEARCH_BACKEND", "sql-like")
if backend not in ["sql-like", "sql-cache"]:
    raise ValueError("Invalid SEARCH_BACKEND value: " + backend)


def search(keywords: List[str], page: int, per_page: int) -> Union[Pagination, MyPagination]:
    if backend == "sql-like":
        return sqllike_search(keywords, page, per_page)
    else:
        return sqlcache_search(keywords, page, per_page)

def search_reviews(keywords: List[str], page: int, per_page: int, current_user) -> Union[Pagination, MyPagination]:
    if backend == "sql-like":
        return sqllike_search_reviews(keywords, page, per_page, current_user)
    else:
        return sqlcache_search_reviews(keywords, page, per_page, current_user)
