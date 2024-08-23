from typing import List
from app import db
from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import or_
from .pagination import MyPagination
from sqlalchemy.sql.expression import literal_column, text
from app.models import (
    User,
    Course,
    CourseRate,
    CourseTerm,
    Teacher,
    Review,
)
import re


filter = lambda x: re.sub(r'''[~`!@#$%^&*{}[]|\\:";'<>?,./，、。：【】（）？“”「」·]''', ' ', x)


def init() -> None:
    pass


def search(keywords: List[str], page: int, per_page: int) -> MyPagination:
    def course_query_with_meta(meta):
        return db.session.query(Course, literal_column(str(meta)).label("_meta"))

    def teacher_match(q, keyword):
        return q.join(Course.teachers).filter(Teacher.name.like("%" + keyword + "%"))

    def exact_match(q, keyword):
        return q.filter(Course.name == keyword)

    def include_match(q, keyword):
        fuzzy_keyword = keyword.replace("%", "")
        return q.filter(Course.name.like("%" + fuzzy_keyword + "%"))

    def fuzzy_match(q, keyword):
        fuzzy_keyword = keyword.replace("%", "")
        return q.filter(
            Course.name.like("%" + "%".join([char for char in fuzzy_keyword]) + "%")
        )

    def courseries_match(q, keyword):
        courseries_keyword = keyword.replace("%", "")
        return q.filter(CourseTerm.courseries.like(keyword + "%")).filter(
            CourseTerm.course_id == Course.id
        )

    def teacher_and_course_match_0(q, keywords):
        return fuzzy_match(teacher_match(q, keywords[0]), keywords[1])

    def teacher_and_course_match_1(q, keywords):
        return fuzzy_match(teacher_match(q, keywords[1]), keywords[0])

    def ordering(query_obj, keywords):
        # This function is very ugly because sqlalchemy generates anon field names for the literal meta field according to the number of union entries.
        # So, queries with different number of keywords have different ordering field names.
        # Expect to refactor this code.
        if len(keywords) == 1:
            ordering_field = "anon_2_anon_3_anon_4_anon_5_"
        else:
            ordering_field = "anon_2_anon_3_anon_4_"
        if len(keywords) >= 3:
            for count in range(5, len(keywords) + 3):
                ordering_field += "anon_" + str(count) + "_"
        ordering_field += "_meta"
        return query_obj.join(CourseRate).order_by(
            text(ordering_field), Course.QUERY_ORDER()
        )

    union_keywords = None
    if len(keywords) >= 2:
        union_keywords = teacher_and_course_match_0(
            course_query_with_meta(0), keywords
        ).union(teacher_and_course_match_1(course_query_with_meta(0), keywords))

    for keyword in keywords:
        union_courses = (
            teacher_match(course_query_with_meta(1), keyword)
            .union(exact_match(course_query_with_meta(2), keyword))
            .union(include_match(course_query_with_meta(3), keyword))
            .union(fuzzy_match(course_query_with_meta(4), keyword))
            .union(courseries_match(course_query_with_meta(0), keyword))
        )
        if union_keywords:
            union_keywords = union_keywords.union(union_courses)
        else:
            union_keywords = union_courses
    ordered_courses = ordering(union_keywords, keywords).group_by(Course.id)

    # manual pagination -- it's too much trouble to use flask_sqlalchemy's Pagination in this specific case
    num_results = ordered_courses.count()
    selections = ordered_courses.offset((page - 1) * per_page).limit(per_page).all()
    course_objs = [s[0] for s in selections]

    pagination = MyPagination(page=page, per_page=per_page, total=num_results, items=course_objs)

    return pagination


def search_reviews(keywords: List[str], page: int, per_page: int, current_user) -> Pagination:
    unioned_query = None
    for keyword in keywords:
        content_query = Review.query.filter(Review.content.like('%' + keyword + '%'))
        if unioned_query is None:
            unioned_query = content_query
        else:
            unioned_query = unioned_query.union(content_query)

        author_query = Review.query.join(Review.author).filter(User.username == keyword).filter(Review.is_anonymous == False).filter(User.is_profile_hidden == False)
        course_query = Review.query.join(Review.course).filter(Course.name.like('%' + keyword + '%'))
        courseries_query = Review.query.join(Review.course).join(CourseTerm).filter(CourseTerm.courseries.like(keyword + '%')).filter(CourseTerm.course_id == Course.id)
        teacher_query = Review.query.join(Review.course).join(Course.teachers).filter(Teacher.name == keyword)
        unioned_query = unioned_query.union(author_query).union(course_query).union(courseries_query).union(teacher_query)

    unioned_query = unioned_query.filter(Review.is_blocked == False).filter(Review.is_hidden == False)
    if not current_user.is_authenticated or current_user.identity != 'Student':
        if current_user.is_authenticated:
            unioned_query = unioned_query.filter(or_(Review.only_visible_to_student == False, Review.author == current_user))
        else:
            unioned_query = unioned_query.filter(Review.only_visible_to_student == False)
    reviews_paged = unioned_query.order_by(Review.update_time.desc()).paginate(page=page, per_page=per_page)
    return reviews_paged
