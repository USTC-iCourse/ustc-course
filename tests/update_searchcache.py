# python -m tests.update_searchcache
# initialize needs time, be patient.
from app import app

from app.models import Course, CourseSearchCache, Review, ReviewSearchCache

if __name__ == "__main__":
    with app.app_context():
        for course in Course.query.all():
            CourseSearchCache.update(course)
        for review in Review.query.all():
            ReviewSearchCache.update(review)
