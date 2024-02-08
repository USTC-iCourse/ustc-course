# python -m tests.update_searchcache
# initialize needs time, be patient.
from app import app
from app.models import Course, CourseSearchCache, Review, ReviewSearchCache
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search cache manage")
    parser.add_argument("--nuke", action="store_true", help="remove search cache tables")
    parser.add_argument("--init-course", action="store_true", help="initialize course cache")
    parser.add_argument("--init-review", action="store_true", help="initialize review cache")
    args = parser.parse_args()

    with app.app_context():
        if args.nuke:
            engine = app.extensions['sqlalchemy'].engine
            CourseSearchCache.__table__.drop(engine)
            ReviewSearchCache.__table__.drop(engine)
            print("search cache tables removed")
            print("Run tests.init_db to recreate them.")

        if args.init_course or args.init_review:
            print("initializing")
            if args.init_course:
                print("course cache")
                for course in Course.query.all():
                    CourseSearchCache.update(course)
            if args.init_review:
                print("review cache")
                for review in Review.query.all():
                    ReviewSearchCache.update(review)
