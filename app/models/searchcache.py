# This module has two classes: CourseSearchCache and ReviewSearchCache
# Data inside shall be preprocessed with jieba, and stored in the database.
# For now as we have jieba, we don't use ngram.
from app import db, app
from .course import Course
from .review import Review
import jieba
import html2text


auto_update = app.config.get("UPDATE_SEARCH_CACHE", False)


class CourseSearchCache(db.Model):
    id = db.Column(
        db.Integer, db.ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True
    )
    text = db.Column(db.Text, nullable=False)

    # mysql full text search index
    __table_args__ = (
        db.Index(
            "text_index", text, mysql_prefix="FULLTEXT", mariadb_prefix="FULLTEXT"
        ),
    )

    @staticmethod
    def process_text(course: Course) -> str:
        # Course name + teacher name(s) + Course ID (courseries)
        course_name = list(jieba.cut_for_search(course.name))
        # use jieba for name, to make it more flexible
        # teacher_names = [teacher.name for teacher in course.teachers]
        teacher_names = []
        for teacher in course.teachers:
            teacher_names.append(teacher.name)
            teacher_names.extend(jieba.cut_for_search(teacher.name))
        # also not for courseries
        try:
            courseries = [course.courseries]
        except AttributeError:
            # it is possible that course has no terms data
            courseries = []
        return " ".join(course_name + teacher_names + courseries)

    @staticmethod
    def update(course: Course, follow_config=False, commit=True):
        if follow_config and not auto_update:
            return
        cache = CourseSearchCache.query.get(course.id)
        if cache is None:
            cache = CourseSearchCache(id=course.id)
        cache.text = CourseSearchCache.process_text(course)
        db.session.add(cache)
        if commit:
            db.session.commit()


class ReviewSearchCache(db.Model):
    id = db.Column(
        db.Integer, db.ForeignKey("reviews.id", ondelete="CASCADE"), primary_key=True
    )
    text = db.Column(db.Text, nullable=False)

    # permission-related fields
    only_visible_to_student = db.Column(db.Boolean, default=False)
    is_hidden = db.Column(db.Boolean, default=False)
    is_blocked = db.Column(db.Boolean, default=False)
    author = db.Column(db.Integer, db.ForeignKey("users.id"))

    # mysql full text search index
    __table_args__ = (
        db.Index(
            "text_index", text, mysql_prefix="FULLTEXT", mariadb_prefix="FULLTEXT"
        ),
    )

    @staticmethod
    def process_text(review: Review) -> str:
        # convert HTML to plain text
        content = html2text.html2text(review.content)
        return " ".join(jieba.cut_for_search(content))

    @staticmethod
    def update(review: Review, follow_config=False, commit=True):
        if follow_config and not auto_update:
            return
        cache = ReviewSearchCache.query.get(review.id)
        if cache is None:
            cache = ReviewSearchCache(id=review.id, author=review.author.id)
        cache.text = ReviewSearchCache.process_text(review)
        cache.is_blocked = review.is_blocked
        cache.is_hidden = review.is_hidden
        cache.only_visible_to_student = review.only_visible_to_student
        db.session.add(cache)
        if commit:
            db.session.commit()
