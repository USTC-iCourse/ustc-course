"""add review_redactions -- per-review partial masking of offending text

Until now an admin handling a complaint had two blunt instruments: block the
whole review, or hand-write a regular expression into ``reviews.filter_rule``
that the frontend applied to the raw HTML.  Neither fits the common case, which
is a handful of characters in an otherwise useful review.

This table records those characters.  It stores the *selected string* rather
than a character range, so the mask survives the author editing the rest of the
review; ``anchor_pos`` is only a snapshot used to pick between occurrences and
to work out, after an edit, whether the author removed the words or tried to
disguise them.  ``app/redaction.py`` explains the reasoning in full.

Nothing here touches ``reviews``: the author's text is never rewritten, and
dropping this table restores the site to unmasked rendering.

Revision ID: c1d4e8f20a37
Revises: 7a2f4c9e1d38
Create Date: 2026-09-02 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = 'c1d4e8f20a37'
down_revision = '7a2f4c9e1d38'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'review_redactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('review_id', sa.Integer(), nullable=True),
        # utf8mb4_bin so the match is exact: a case- or width-insensitive
        # collation would let a lookup here disagree with the JS, which
        # compares strings verbatim.
        sa.Column('quote', sa.String(length=200, collation='utf8mb4_bin'), nullable=False),
        sa.Column('anchor_pos', sa.Integer(), nullable=True),
        sa.Column('scope', sa.String(length=8), nullable=True),
        sa.Column('reason', sa.String(length=32), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_by_id', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['review_id'], ['reviews.id']),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['revoked_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        mysql_engine='InnoDB',
    )
    op.create_index('ix_review_redactions_review_id', 'review_redactions', ['review_id'])
    # Every page render asks for the active rows and nothing else, so the
    # status index carries the read path.
    op.create_index('ix_review_redactions_status', 'review_redactions', ['status'])


def downgrade():
    op.drop_index('ix_review_redactions_status', table_name='review_redactions')
    op.drop_index('ix_review_redactions_review_id', table_name='review_redactions')
    op.drop_table('review_redactions')
