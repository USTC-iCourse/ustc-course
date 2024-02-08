from . import sqllike, sqlcache
from flask_sqlalchemy.pagination import Pagination
from .pagination import MyPagination
from typing import List, Union
from app import app


backend = app.config.get("SEARCH_BACKEND", "sql-like")
if backend not in ["sql-like", "sql-cache"]:
    raise ValueError("Invalid SEARCH_BACKEND value: " + backend)

def filter(x):
    if backend == "sql-like":
        return sqllike.filter(x)
    else:
        return sqlcache.filter(x)

def search(keywords: List[str], page: int, per_page: int) -> Union[Pagination, MyPagination]:
    if backend == "sql-like":
        return sqllike.search(keywords, page, per_page)
    else:
        return sqlcache.search(keywords, page, per_page)

def search_reviews(keywords: List[str], page: int, per_page: int, current_user) -> Union[Pagination, MyPagination]:
    if backend == "sql-like":
        return sqllike.search_reviews(keywords, page, per_page, current_user)
    else:
        return sqlcache.search_reviews(keywords, page, per_page, current_user)
