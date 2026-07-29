"""initial schema

Revision ID: 001
Revises: 
Create Date: 2026-07-27
"""
import sqlalchemy as sa

from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "templates",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(), nullable=False, index=True),
        sa.Column("platform", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), default=sa.func.now()),
        sa.Column("version", sa.Integer(), default=1),
        sa.Column("is_active", sa.Boolean(), default=True)
    )
    op.create_table(
        "template_variables",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("template_id", sa.String(), sa.ForeignKey("templates.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("required", sa.Boolean(), default=True),
        sa.Column("default", sa.JSON(), nullable=True),
        sa.Column("description", sa.String(), nullable=True)
    )
    op.create_table(
        "message_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("message_id", sa.String(), nullable=False, index=True),
        sa.Column("platform", sa.String(), nullable=False, index=True),
        sa.Column("direction", sa.String(), nullable=False),
        sa.Column("sender_id", sa.String(), nullable=True),
        sa.Column("recipient_id", sa.String(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(), nullable=True, index=True),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("sentiment", sa.String(), nullable=True),
        sa.Column("draft_id", sa.String(), nullable=True),
        sa.Column("template_used", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), default=sa.func.now(), index=True),
        sa.Column("processing_time", sa.Float(), nullable=True)
    )
    op.create_table(
        "metrics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("metric_type", sa.String(), nullable=False, index=True),
        sa.Column("platform", sa.String(), nullable=True, index=True),
        sa.Column("intent", sa.String(), nullable=True),
        sa.Column("value", sa.Integer(), default=1),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), default=sa.func.now(), index=True)
    )

def downgrade() -> None:
    op.drop_table("metrics")
    op.drop_table("message_logs")
    op.drop_table("template_variables")
    op.drop_table("templates")
