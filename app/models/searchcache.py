# This module has two classes: CourseSearchCache and ReviewSearchCache
# Data inside shall be preprocessed with jieba, and stored in the database.
# For now as we have jieba, we don't use ngram.
import os
from app import db, app
from .course import Course
from .review import Review
import jieba
import html2text


auto_update = app.config.get("UPDATE_SEARCH_CACHE", False)
jieba.dt.tmp_dir = os.path.expanduser("~/.cache/jieba")
os.makedirs(jieba.dt.tmp_dir, exist_ok=True)


# To handle these queries:
# "编译原理与技术" -> "编译原理和技术"
# "数据分析与实践" -> "数据分析及实践"
# "概率论和数理统计" -> "概率论与数理统计"
def is_chinese_stop_char(c: str) -> bool:
    STOP = ["与", "和", "及", "，", "、", "。", "：", "（", "）", "【", "】"]
    return c in STOP


class CourseSearchCache(db.Model):
    id = db.Column(
        db.Integer, db.ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True
    )
    # Set collation to utf8mb4_unicode_ci to handling queries like "英语交流Ⅰ" -> "英语交流I"
    text = db.Column(db.Text(collation="utf8mb4_unicode_ci"), nullable=False)

    # mysql full text search index
    __table_args__ = (
        db.Index(
            "text_index", text, mysql_prefix="FULLTEXT", mariadb_prefix="FULLTEXT"
        ),
    )

    @staticmethod
    def process_text(course: Course) -> str:
        # Course name + teacher name(s)
        course_name = jieba.lcut_for_search(course.name)
        # use jieba for name, to make it more flexible
        # teacher_names = [teacher.name for teacher in course.teachers]
        teacher_names = []
        for teacher in course.teachers:
            teacher_names.append(teacher.name)
            cutted = jieba.lcut_for_search(teacher.name)
            if len(cutted) > 1:
                teacher_names.extend(cutted)
        # For some queries it is impossible to use Chinese word segmentation methods to match
        # like "程设" for "程序设计", "大物实验" for "大学物理-基础实验"
        # so we need to get every single character in current text, and sepearte by space
        # to make it possible to match.
        allchars = set()
        for word in course_name + teacher_names:
            for char in word:
                if not is_chinese_stop_char(char):
                    allchars.add(char)
        return " ".join(course_name + teacher_names + list(allchars))

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
    text = db.Column(db.Text(collation="utf8mb4_unicode_ci"), nullable=False)

    # mysql full text search index
    __table_args__ = (
        db.Index(
            "text_index", text, mysql_prefix="FULLTEXT", mariadb_prefix="FULLTEXT"
        ),
    )

    @staticmethod
    def process_text(review: Review) -> str:
        keywords = []
        if review.course:
            course_metadata_weight = 5  # course metadata match is more important than review content match
            keywords = [CourseSearchCache.process_text(review.course) for _ in range(course_metadata_weight)]
        # convert HTML to plain text
        content = html2text.html2text(review.content)
        review_keywords = " ".join(jieba.cut_for_search(content))
        keywords.append(review_keywords)
        return " ".join(keywords)

    @staticmethod
    def update(review: Review, follow_config=False, commit=True):
        if follow_config and not auto_update:
            return
        cache = ReviewSearchCache.query.get(review.id)
        if cache is None:
            cache = ReviewSearchCache(id=review.id)
        cache.text = ReviewSearchCache.process_text(review)
        db.session.add(cache)
        if commit:
            db.session.commit()
