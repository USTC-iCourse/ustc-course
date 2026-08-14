"""drop the SQL search caches and the one-time search token table

Search no longer runs against MySQL FULLTEXT.  ``app.search`` builds its own
memory-mapped index out of band (``python3 -m app.search.builder``), so the two
cache tables are dead weight -- ``review_search_cache`` alone held 65 MB,
mostly because every review carried five copies of its course's text to weight
it in the ranking.

``search_tokens`` goes with the one-time token scheme it backed.  That scheme
allowed a token to be reused from the same IP address, so it never limited
anything an attacker would do, while breaking search for clients without
JavaScript and making search URLs unshareable.  Search now answers from a
memory-mapped index in single-digit milliseconds and needs no gate of its own.

Nothing here holds data that cannot be regenerated: the caches are derived from
``courses``/``reviews``, and the tokens are ephemeral by design.  The downgrade
recreates the schema (empty); re-populating the caches would mean restoring the
old engine as well.

Revision ID: 7a2f4c9e1d38
Revises: 5b6c02ef6a69
Create Date: 2026-08-14 18:20:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = '7a2f4c9e1d38'
down_revision = '5b6c02ef6a69'
branch_labels = None
depends_on = None

_TABLES = ('review_search_cache', 'course_search_cache', 'search_tokens')


def _existing(names):
    bind = op.get_bind()
    present = set(sa.inspect(bind).get_table_names())
    return [name for name in names if name in present]


def upgrade():
    # Tolerate a database where one of these was never created (a fresh
    # install that has only ever run the new engine).
    for table in _existing(_TABLES):
        op.drop_table(table)


def downgrade():
    op.create_table(
        'course_search_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(collation='utf8mb4_unicode_ci'), nullable=False),
        sa.ForeignKeyConstraint(['id'], ['courses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB',
    )
    op.create_index('text_index', 'course_search_cache', ['text'], mysql_prefix='FULLTEXT')

    op.create_table(
        'review_search_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('text', mysql.LONGTEXT(collation='utf8mb4_unicode_ci'), nullable=False),
        sa.ForeignKeyConstraint(['id'], ['reviews.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB',
    )
    op.create_index('text_index', 'review_search_cache', ['text'], mysql_prefix='FULLTEXT')

    op.create_table(
        'search_tokens',
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.PrimaryKeyConstraint('token'),
        mysql_engine='InnoDB',
    )
