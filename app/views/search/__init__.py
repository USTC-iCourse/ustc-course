from . import sqllike, sqlcache
from flask_sqlalchemy.pagination import Pagination
from .pagination import MyPagination
from typing import List, Union
from app import app


def get_backend():
    # put config get in function to help test scripts like tests.search_eval work
    backend = app.config.get("SEARCH_BACKEND", "sql-like")
    if backend not in ["sql-like", "sql-cache"]:
        raise ValueError("Invalid SEARCH_BACKEND value: " + backend)
    return backend

if get_backend() == "sql-like":
    sqllike.init()
else:
    sqlcache.init()


def filter(x: str) -> str:
    if get_backend() == "sql-like":
        return sqllike.filter(x)
    else:
        return sqlcache.filter(x)

def search(keywords: List[str], page: int, per_page: int, exact: bool) -> Union[Pagination, MyPagination]:
    if get_backend() == "sql-like" or exact: # exact search only needs sql-like backend
        return sqllike.search(keywords, page, per_page, exact)
    else:
        return sqlcache.search(keywords, page, per_page)

def search_courses(keyword: List[str]) -> List[str]:
    if get_backend() == "sql-like":
        return sqllike.search_courses(keyword)
    else:
        return sqlcache.search_courses(keyword)

def search_reviews(keywords: List[str], page: int, per_page: int, current_user) -> Union[Pagination, MyPagination]:
    if get_backend() == "sql-like":
        return sqllike.search_reviews(keywords, page, per_page, current_user)
    else:
        return sqlcache.search_reviews(keywords, page, per_page, current_user)
