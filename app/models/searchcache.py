# This module has two classes: CourseSearchCache and ReviewSearchCache
# Data inside shall be preprocessed with jieba, and stored in the database.
# For now as we have jieba, we don't use ngram.
from app import db
from .course import Course
from .review import Review
import jieba
import html2text

class CourseSearchCache(db.Model):
    id = db.Column(db.Integer, db.ForeignKey('courses.id', ondelete='CASCADE'), primary_key=True)
    text = db.Column(db.Text, nullable=False)

    # mysql full text search index
    __table_args__ = (
        db.Index("text_index", text, mysql_prefix="FULLTEXT", mariadb_prefix="FULLTEXT"),
    )

    @staticmethod
    def process_text(course: Course) -> str:
        # Course name + teacher name(s) + Course ID (courseries)
        course_name = list(jieba.cut_for_search(course.name))
        # well, we don't have to use jieba for teacher names.
        teacher_names = [teacher.name for teacher in course.teachers]
        # also not for courseries
        courseries = [course.courseries]
        return " ".join(course_name + teacher_names + courseries)
    
    @staticmethod
    def update(course: Course):
        cache = CourseSearchCache.query.get(course.id)
        if cache is None:
            cache = CourseSearchCache(id=course.id)
        cache.text = CourseSearchCache.process_text(course)
        db.session.add(cache)
        db.session.commit()


class ReviewSearchCache(db.Model):
    id = db.Column(db.Integer, db.ForeignKey('reviews.id', ondelete='CASCADE'), primary_key=True)
    text = db.Column(db.Text, nullable=False)

    # mysql full text search index
    __table_args__ = (
        db.Index("text_index", text, mysql_prefix="FULLTEXT", mariadb_prefix="FULLTEXT"),
    )

    @staticmethod
    def process_text(review: Review) -> str:
        # convert HTML to plain text
        content = html2text.html2text(review.content)
        return " ".join(jieba.cut_for_search(content))
    
    @staticmethod
    def update(review: Review):
        cache = ReviewSearchCache.query.get(review.id)
        if cache is None:
            cache = ReviewSearchCache(id=review.id)
        cache.text = ReviewSearchCache.process_text(review)
        db.session.add(cache)
        db.session.commit()
