"""baseline: adopt Alembic on the existing production schema

This is an intentional no-op. The production database predates migrations,
so we stamp it at this revision and start tracking changes from here
(``flask db stamp 5b6c02ef6a69`` — already done on production 2026-07-23).

Known model-vs-production drift at the time of adoption (left as-is on
purpose; autogenerate may re-detect some of it until it is cleaned up):

* Legacy tables with no model: old_courses, related_courses
  (hidden from autogenerate by the include_object filter in env.py)
* Foreign keys declared in models but absent in the DB
  (reviews, notes, course_rates, course_teachers, *_course join tables, ...)
* Historical index names (key_name/key_term/idx_*) vs model names (ix_*),
  and some count/rate indexes missing on course_rates
* Columns present in DB but not in models: courses.teacher_list,
  course_terms.homepage/introduction, course_time_locations.term
* Minor nullability mismatches (join_course, reviews.is_hidden,
  review_search_cache.text)

Revision ID: 5b6c02ef6a69
Revises:
Create Date: 2026-07-23 14:11:46.922744

"""

# revision identifiers, used by Alembic.
revision = '5b6c02ef6a69'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
