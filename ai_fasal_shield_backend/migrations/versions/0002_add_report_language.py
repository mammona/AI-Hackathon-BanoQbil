"""add report language

Revision ID: 0002
Revises: 0001
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "reports",
        sa.Column(
            "language",
            sa.String(length=20),
            nullable=False,
            server_default="urdu",
        ),
    )
    op.create_index("ix_reports_language", "reports", ["language"])


def downgrade() -> None:
    op.drop_index("ix_reports_language", table_name="reports")
    op.drop_column("reports", "language")
