"""create reports table

Revision ID: 0001
Revises:
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("report_id", sa.String(length=100), nullable=False),
        sa.Column("selected_crop", sa.String(length=32), nullable=False),
        sa.Column("detected_crop", sa.String(length=32)),
        sa.Column("image_status", sa.String(length=40), nullable=False),
        sa.Column("crop_match", sa.Boolean()),
        sa.Column("crop_validation_confidence", sa.Float()),
        sa.Column("disease", sa.String(length=100)),
        sa.Column("disease_confidence", sa.Float()),
        sa.Column("disease_confidence_level", sa.String(length=20)),
        sa.Column("question_1_raw", sa.Text(), nullable=False),
        sa.Column("question_2_raw", sa.Text(), nullable=False),
        sa.Column("question_3_raw", sa.Text(), nullable=False),
        sa.Column("question_4_raw", sa.Text(), nullable=False),
        sa.Column("symptoms", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("symptom_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("symptom_mapping", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("symptom_dictionary_version", sa.String(length=20)),
        sa.Column("affected_part", sa.String(length=100)),
        sa.Column("problem_duration", sa.String(length=100)),
        sa.Column("affected_area", sa.String(length=100)),
        sa.Column("spread_status", sa.String(length=100)),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("recommended_next_step", sa.Text(), nullable=False),
        sa.Column("requires_expert_review", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("image_path", sa.Text()),
        sa.Column("processing_status", sa.String(length=60), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("report_id"),
    )
    for col in [
        "report_id",
        "selected_crop",
        "detected_crop",
        "image_status",
        "disease",
        "spread_status",
        "requires_expert_review",
        "latitude",
        "longitude",
        "processing_status",
        "reported_at",
    ]:
        op.create_index(f"ix_reports_{col}", "reports", [col])


def downgrade() -> None:
    op.drop_table("reports")
