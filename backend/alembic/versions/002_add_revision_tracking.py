"""Add revision tracking to feedback_history.

Revision ID: 002_revision_tracking
Revises: 001_initial
Create Date: 2025-01-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002_revision_tracking"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add revision tracking columns to feedback_history
    op.add_column(
        "feedback_history",
        sa.Column("previous_feedback_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "feedback_history",
        sa.Column("revision_number", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "feedback_history",
        sa.Column("is_passing", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Create foreign key constraint for self-referential relationship
    op.create_foreign_key(
        "fk_feedback_history_previous",
        "feedback_history",
        "feedback_history",
        ["previous_feedback_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Create index for efficient revision chain queries
    op.create_index(
        "ix_feedback_history_previous_id",
        "feedback_history",
        ["previous_feedback_id"],
    )

    # Create composite index for finding latest feedback per issue
    op.create_index(
        "ix_feedback_history_issue_revision",
        "feedback_history",
        ["user_id", "issue_key", "revision_number"],
    )


def downgrade() -> None:
    op.drop_index("ix_feedback_history_issue_revision", table_name="feedback_history")
    op.drop_index("ix_feedback_history_previous_id", table_name="feedback_history")
    op.drop_constraint("fk_feedback_history_previous", "feedback_history", type_="foreignkey")
    op.drop_column("feedback_history", "is_passing")
    op.drop_column("feedback_history", "revision_number")
    op.drop_column("feedback_history", "previous_feedback_id")
