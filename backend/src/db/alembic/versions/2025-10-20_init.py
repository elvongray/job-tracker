"""init

Revision ID: 2abdd0c64d1b
Revises:
Create Date: 2025-10-20 12:54:37.404053

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2abdd0c64d1b"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ENUM_DEFINITIONS = {
    "app_status": (
        "Draft",
        "Applied",
        "Screening",
        "Recruiter_Call",
        "Tech_Screen",
        "Interview_Loop",
        "Offer",
        "Accepted",
        "Declined",
        "Rejected",
        "On_Hold",
    ),
    "priority_level": ("None", "Low", "Medium", "High"),
    "location_mode": ("remote", "onsite", "hybrid"),
    "activity_type": ("Interview", "FollowUp", "Call", "Email", "Other"),
    "activity_status": ("scheduled", "done", "canceled"),
    "interview_stage": ("screening", "technical", "loop", "offer", "other"),
    "interview_medium": ("onsite", "zoom", "phone", "google_meet", "teams", "other"),
    "followup_channel": ("email", "linkedin", "phone", "other"),
    "reminder_channel": ("in_app", "email", "calendar"),
}


def _create_enum_if_not_exists(bind, name: str, values: tuple[str, ...]) -> None:
    formatted_values = ", ".join(f"'{value}'" for value in values)
    statement = sa.text(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = :enum_name) THEN
                CREATE TYPE {name} AS ENUM ({formatted_values});
            END IF;
        END
        $$;
        """
    )
    bind.execute(statement, {"enum_name": name})


def _drop_enum_if_exists(bind, name: str) -> None:
    statement = sa.text(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = :enum_name) THEN
                DROP TYPE {name} CASCADE;
            END IF;
        END
        $$;
        """
    )
    bind.execute(statement, {"enum_name": name})


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    for enum_name, enum_values in ENUM_DEFINITIONS.items():
        _create_enum_if_not_exists(bind, enum_name, enum_values)

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("session_timeout_mins", sa.Integer(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "user_settings",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("quiet_hours_start", sa.Time(timezone=False), nullable=True),
        sa.Column("quiet_hours_end", sa.Time(timezone=False), nullable=True),
        sa.Column("reminder_defaults", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_user_settings_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_user_settings")),
    )

    op.create_table(
        "applications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("role_title", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                *ENUM_DEFINITIONS["app_status"],
                name="app_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("application_date", sa.Date(), nullable=False),
        sa.Column(
            "priority",
            postgresql.ENUM(
                *ENUM_DEFINITIONS["priority_level"],
                name="priority_level",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "location_mode",
            postgresql.ENUM(
                *ENUM_DEFINITIONS["location_mode"],
                name="location_mode",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("location_text", sa.String(length=255), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("job_url", sa.String(length=1024), nullable=True),
        sa.Column("salary_min", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("salary_max", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("salary_currency", sa.String(length=8), nullable=True),
        sa.Column("job_requisition_id", sa.String(length=128), nullable=True),
        sa.Column("seniority_level", sa.String(length=128), nullable=True),
        sa.Column("tech_keywords", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("resume_url", sa.String(length=1024), nullable=True),
        sa.Column("cover_letter_url", sa.String(length=1024), nullable=True),
        sa.Column("cover_letter_used", sa.Boolean(), nullable=True),
        sa.Column("contacts_inline", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("next_action", sa.String(length=255), nullable=True),
        sa.Column("next_action_due", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("attachments_links", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(salary_min IS NULL OR salary_max IS NULL) OR (salary_min <= salary_max)",
            name=op.f("ck_applications_ck_applications_salary_range"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_applications_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_applications")),
    )
    op.create_index("ix_applications_user_id_status", "applications", ["user_id", "status"], unique=False)
    op.create_index("ix_applications_user_id_archived_at", "applications", ["user_id", "archived_at"], unique=False)
    op.create_index("ix_applications_user_id_next_action_due", "applications", ["user_id", "next_action_due"], unique=False)
    op.create_index(
        "ix_applications_user_id_created_at_desc",
        "applications",
        [sa.text("user_id"), sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index("ix_applications_tags_gin", "applications", ["tags"], unique=False, postgresql_using="gin")

    op.create_table(
        "activities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column(
            "type",
            postgresql.ENUM(
                *ENUM_DEFINITIONS["activity_type"],
                name="activity_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                *ENUM_DEFINITIONS["activity_status"],
                name="activity_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("outcome", sa.String(length=255), nullable=True),
        sa.Column("next_action", sa.String(length=255), nullable=True),
        sa.Column("next_action_due", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("related_contacts", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "interview_stage",
            postgresql.ENUM(
                *ENUM_DEFINITIONS["interview_stage"],
                name="interview_stage",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "interview_medium",
            postgresql.ENUM(
                *ENUM_DEFINITIONS["interview_medium"],
                name="interview_medium",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("location_or_link", sa.String(length=512), nullable=True),
        sa.Column("agenda", sa.Text(), nullable=True),
        sa.Column("prep_checklist", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "followup_channel",
            postgresql.ENUM(
                *ENUM_DEFINITIONS["followup_channel"],
                name="followup_channel",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("template_used", sa.String(length=255), nullable=True),
        sa.Column("reply_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status != 'scheduled' OR starts_at IS NOT NULL",
            name=op.f("ck_activities_ck_activities_scheduled_requires_starts_at"),
        ),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], name=op.f("fk_activities_application_id_applications"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_activities_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_activities")),
    )
    op.create_index("ix_activities_user_id_next_action_due", "activities", ["user_id", "next_action_due"], unique=False)
    op.create_index("ix_activities_user_id_starts_at", "activities", ["user_id", "starts_at"], unique=False)

    op.create_table(
        "reminders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=True),
        sa.Column("activity_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "channels",
            postgresql.ARRAY(
                postgresql.ENUM(
                    *ENUM_DEFINITIONS["reminder_channel"],
                    name="reminder_channel",
                    create_type=False,
                )
            ),
            nullable=False,
        ),
        sa.Column("sent", sa.Boolean(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(application_id IS NOT NULL) OR (activity_id IS NOT NULL)",
            name=op.f("ck_reminders_ck_reminders_application_or_activity"),
        ),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"], name=op.f("fk_reminders_activity_id_activities"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], name=op.f("fk_reminders_application_id_applications"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_reminders_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reminders")),
        sa.UniqueConstraint("user_id", "dedupe_key", name="uq_reminders_user_dedupe_key"),
    )
    op.create_index(
        "ix_reminders_user_id_due_at_pending",
        "reminders",
        ["user_id", "due_at"],
        unique=False,
        postgresql_where=sa.text("sent = false"),
    )

    op.create_table(
        "magic_link_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_magic_link_tokens_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_magic_link_tokens")),
        sa.UniqueConstraint("token", name="uq_magic_link_tokens_token"),
    )
    op.create_index("ix_magic_link_tokens_expires_at", "magic_link_tokens", ["expires_at"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_magic_link_tokens_expires_at", table_name="magic_link_tokens")
    op.drop_table("magic_link_tokens")

    op.drop_index("ix_reminders_user_id_due_at_pending", table_name="reminders", postgresql_where=sa.text("sent = false"))
    op.drop_table("reminders")

    op.drop_index("ix_activities_user_id_starts_at", table_name="activities")
    op.drop_index("ix_activities_user_id_next_action_due", table_name="activities")
    op.drop_table("activities")

    op.drop_index("ix_applications_tags_gin", table_name="applications", postgresql_using="gin")
    op.drop_index("ix_applications_user_id_created_at_desc", table_name="applications")
    op.drop_index("ix_applications_user_id_next_action_due", table_name="applications")
    op.drop_index("ix_applications_user_id_archived_at", table_name="applications")
    op.drop_index("ix_applications_user_id_status", table_name="applications")
    op.drop_table("applications")

    op.drop_table("user_settings")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    for enum_name in reversed(list(ENUM_DEFINITIONS.keys())):
        _drop_enum_if_exists(bind, enum_name)
