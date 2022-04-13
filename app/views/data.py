from flask import Blueprint,render_template,abort,redirect,url_for,request,abort,jsonify
from flask_login import login_required
from flask_babel import gettext as _
from app.models import *
from app import db
from app.utils import sanitize
from sqlalchemy import or_, func, sql

data = Blueprint('data',__name__)


@data.route('/')
def index():
    teacher_rank_join = sql.join(Teacher, sql.join(course_teachers, sql.join(Course, Review, Course.id == Review.course_id), course_teachers.c.course_id == Course.id), course_teachers.c.teacher_id == Teacher.id)
    filter_teacher_with_any_low_rating_course = Teacher.id.not_in(sql.select(Teacher.id).join(course_teachers).join(Course).join(CourseRate).filter(CourseRate._rate_average < 8))
    teacher_query_with_high_rating_course = sql.select(Teacher.id.label('teacher_id'), func.count(CourseRate.id).label('course_count')).select_from(sql.join(Teacher, sql.join(course_teachers, CourseRate, course_teachers.c.course_id == CourseRate.id), Teacher.id == course_teachers.c.teacher_id)).filter(CourseRate._rate_average > 9).group_by(Teacher.id)
    teachers_with_high_rating_course = db.session.query(db.text('teacher_id')).select_from(teacher_query_with_high_rating_course).filter(db.text('course_count >= 3')).all()
    teachers_with_high_rating_course = [teacher[0] for teacher in teachers_with_high_rating_course]
    teacher_rank_unordered = (db.session.query(Teacher.id.label('teacher_id'),
                                               Teacher.name.label('teacher_name'),
                                               func.count(func.distinct(Course.id)).label('course_count'),
                                               func.count(Review.id).label('review_count'),
                                               func.avg(Review.rate).label('avg_review_rate'),
                                               func.sum(Review.rate).label('total_review_rate'))
                              .select_from(teacher_rank_join)
                              .filter(filter_teacher_with_any_low_rating_course)
                              .filter(Teacher.id.in_(teachers_with_high_rating_course))
                              .group_by(Teacher.id)
                              .subquery())
    teacher_rank = (db.session.query(db.text('teacher_id'), db.text('teacher_name'), db.text('course_count'), db.text('review_count'), db.text('avg_review_rate'), db.text('total_review_rate'))
                              .select_from(teacher_rank_unordered)
                              .order_by(Course.generic_query_order(db.text('total_review_rate'), db.text('review_count')).desc())
                              .limit(10).all())

    teachers_with_most_high_rated_courses = (
                              db.session.query(Teacher.id.label('teacher_id'),
                                               Teacher.name.label('teacher_name'),
                                               func.count(func.distinct(Course.id)).label('course_count'),
                                               func.count(Review.id).label('review_count'),
                                               func.avg(Review.rate).label('avg_review_rate'),
                                               func.sum(Review.rate).label('total_review_rate'))
                              .select_from(teacher_rank_join)
                              .filter(filter_teacher_with_any_low_rating_course)
                              .filter(Teacher.id.in_(teachers_with_high_rating_course))
                              .group_by(Teacher.id)
                              .order_by(db.text('course_count desc'), db.text('avg_review_rate desc'))
                              .limit(10).all())

    user_rank = (db.session.query(User.id, User.username, func.count(Review.id).label('reviews_count'))
                           .join(User)
                           .group_by(Review.author_id)
                           .order_by(db.text('reviews_count desc'))
                           .limit(10).all())

    review_rank_join = sql.join(User, sql.join(Course, sql.join(review_upvotes, Review, review_upvotes.c.review_id == Review.id), Course.id == Review.course_id), User.id == Review.author_id)
    review_rank_query = db.session.query(Course.id.label('course_id'),
                                         Course.name.label('course_name'),
                                         Review.id.label('review_id'),
                                         User.id.label('author_id'),
                                         User.username.label('author_username'),
                                         func.count(review_upvotes.c.author_id).label('review_upvotes_count'))
    review_rank = (review_rank_query.select_from(review_rank_join)
                                    .filter(func.length(Review.content) >= 100 * 2)
                                    .group_by(review_upvotes.c.review_id)
                                    .order_by(db.text('review_upvotes_count desc'))
                                    .limit(10).all())

    top_rated_courses = (Course.query.join(CourseRate)
                               .filter(CourseRate.review_count >= 20)
                               .order_by(Course.QUERY_ORDER())
                               .limit(10).all())
    worst_rated_courses = (Course.query.join(CourseRate)
                                 .filter(CourseRate.review_count >= 10)
                                 .order_by(Course.REVERSE_QUERY_ORDER())
                                 .limit(10).all())
    popular_courses = (Course.query.join(CourseRate)
                             .order_by(CourseRate.review_count.desc(), CourseRate._rate_average.desc())
                             .limit(10).all())
    return render_template('data.html', teachers_with_most_high_rated_courses=teachers_with_most_high_rated_courses, teachers=teacher_rank, users=user_rank, reviews=review_rank, top_rated_courses=top_rated_courses, worst_rated_courses=worst_rated_courses, popular_courses=popular_courses)


@data.route('/teachers')
def teacher_ranking():
    return render_template('data.html')


@data.route('/users')
def user_ranking():
    return render_template('data.html')


@data.route('/reviews')
def review_ranking():
    return render_template('data.html')


@data.route('/history')
def view_history():
    return render_template('data.html')

@data.route('/stats/')
def view_stats():
    site_stat = dict()
    site_stat['user_count'] = User.query.count()
    site_stat['course_count'] = Course.query.count()
    site_stat['review_count'] = Review.query.count()
    site_stat['teacher_count'] = Teacher.query.count()
    site_stat['registered_teacher_count'] = User.query.filter(User.identity == 'Teacher').count()

    course_review_counts = db.session.query(func.count(Review.id).label('review_count')).group_by(Review.course_id).subquery()
    course_review_count_dist = db.session.query(db.text('review_count'), func.count().label('course_count')).select_from(course_review_counts).group_by(db.text('review_count')).order_by(db.text('review_count')).all()

    user_review_counts = db.session.query(func.count(func.distinct(Review.id)).label('review_count'), func.count().label('review_upvote_count')).select_from(sql.join(Review, review_upvotes, Review.author_id == review_upvotes.c.author_id)).group_by(Review.author_id).subquery()
    user_review_count_dist = db.session.query(db.text('review_count'), db.text('review_upvote_count'), func.count().label('user_count')).select_from(user_review_counts).group_by(db.text('review_count')).order_by(db.text('review_count')).all()

    review_dates = db.session.query(func.year(Review.publish_time).label('publish_year'), func.month(Review.publish_time).label('publish_month'), func.count().label('review_count')).group_by(db.text('publish_year'), db.text('publish_month')).order_by(db.text('publish_year'), db.text('publish_month')).all()

    user_reg_dates = db.session.query(func.year(User.register_time).label('reg_year'), func.month(User.register_time).label('reg_month'), func.count().label('user_count')).group_by(db.text('reg_year'), db.text('reg_month')).order_by(db.text('reg_year'), db.text('reg_month')).all()

    return render_template('stats.html', site_stat=site_stat, course_review_count_dist=course_review_count_dist, user_review_count_dist=user_review_count_dist, review_dates=review_dates, user_reg_dates=user_reg_dates)
