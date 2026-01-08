"""Initial schema with all models.

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # Jira credentials table
    op.create_table(
        "jira_credentials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("base_url", sa.String(500), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("encrypted_api_token", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jira_credentials_user_id", "jira_credentials", ["user_id"])

    # Telegram user links table
    op.create_table(
        "telegram_user_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("telegram_chat_id", sa.String(100), nullable=True),
        sa.Column("telegram_username", sa.String(100), nullable=True),
        sa.Column("verification_code", sa.String(20), nullable=True),
        sa.Column("code_expires_at", sa.DateTime(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notifications_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_telegram_user_links_user_id", "telegram_user_links", ["user_id"], unique=True)
    op.create_index("ix_telegram_user_links_chat_id", "telegram_user_links", ["telegram_chat_id"])

    # Refresh tokens table
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(500), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_refresh_tokens_token", "refresh_tokens", ["token"], unique=True)
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    # User rubric configs table
    op.create_table(
        "user_rubric_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("min_description_words", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("require_acceptance_criteria", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("allowed_labels", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_rubric_configs_user_id", "user_rubric_configs", ["user_id"])

    # Rubric rules table
    op.create_table(
        "rubric_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("config_id", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.String(50), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("thresholds", postgresql.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["config_id"], ["user_rubric_configs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rubric_rules_config_id", "rubric_rules", ["config_id"])

    # Ambiguous terms table
    op.create_table(
        "ambiguous_terms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("config_id", sa.Integer(), nullable=False),
        sa.Column("term", sa.String(100), nullable=False),
        sa.ForeignKeyConstraint(["config_id"], ["user_rubric_configs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ambiguous_terms_config_id", "ambiguous_terms", ["config_id"])

    # Feedback history table
    op.create_table(
        "feedback_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("issue_key", sa.String(50), nullable=False),
        sa.Column("issue_summary", sa.String(500), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("emoji", sa.String(10), nullable=False),
        sa.Column("overall_assessment", sa.Text(), nullable=False),
        sa.Column("strengths", postgresql.JSON(), nullable=False),
        sa.Column("improvements", postgresql.JSON(), nullable=False),
        sa.Column("suggestions", postgresql.JSON(), nullable=False),
        sa.Column("rubric_breakdown", postgresql.JSON(), nullable=False),
        sa.Column("improved_ac", sa.Text(), nullable=True),
        sa.Column("resources", postgresql.JSON(), nullable=True),
        sa.Column("issue_type", sa.String(50), nullable=True),
        sa.Column("issue_status", sa.String(50), nullable=True),
        sa.Column("assignee", sa.String(255), nullable=True),
        sa.Column("labels", postgresql.JSON(), nullable=True),
        sa.Column("was_posted_to_jira", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("was_sent_to_telegram", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("job_id", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feedback_history_user_id", "feedback_history", ["user_id"])
    op.create_index("ix_feedback_history_issue_key", "feedback_history", ["issue_key"])
    op.create_index("ix_feedback_history_created_at", "feedback_history", ["created_at"])

    # Analysis jobs table
    op.create_table(
        "analysis_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.String(50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("jql", sa.Text(), nullable=True),
        sa.Column("issue_keys", postgresql.JSON(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("total_issues", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_issues", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_issues", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analysis_jobs_job_id", "analysis_jobs", ["job_id"], unique=True)
    op.create_index("ix_analysis_jobs_user_id", "analysis_jobs", ["user_id"])
    op.create_index("ix_analysis_jobs_status", "analysis_jobs", ["status"])


def downgrade() -> None:
    op.drop_table("analysis_jobs")
    op.drop_table("feedback_history")
    op.drop_table("ambiguous_terms")
    op.drop_table("rubric_rules")
    op.drop_table("user_rubric_configs")
    op.drop_table("refresh_tokens")
    op.drop_table("telegram_user_links")
    op.drop_table("jira_credentials")
    op.drop_table("users")
