"""Add confirmed board-photo marking evidence without storing image bytes."""

from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "visual_evidence",
        sa.Column("sequence", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("identifier", sa.Text(), nullable=False),
        sa.Column("image_sha256", sa.Text(), nullable=False),
        sa.Column("marking", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("confidence_ppm", sa.Integer(), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("confirmed_at", sa.Text(), nullable=False),
        sa.UniqueConstraint("identifier", "image_sha256", "marking", "role", name="uq_visual_evidence_claim"),
    )
    op.create_index("ix_visual_evidence_identifier", "visual_evidence", ["identifier"])


def downgrade() -> None:
    op.drop_index("ix_visual_evidence_identifier", table_name="visual_evidence")
    op.drop_table("visual_evidence")
