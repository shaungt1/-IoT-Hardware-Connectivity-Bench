"""Add bounded inspection and test evidence history."""

from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inspection_snapshots",
        sa.Column("sequence", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("identifier", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.Text(), nullable=False),
        sa.Column("inspection_json", sa.Text(), nullable=False),
        sa.Column("recorded_at", sa.Text(), nullable=False),
    )
    op.create_index("ix_inspection_snapshots_identifier", "inspection_snapshots", ["identifier"])
    op.create_table(
        "test_results",
        sa.Column("sequence", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("identifier", sa.Text(), nullable=False),
        sa.Column("test_id", sa.Text(), nullable=False),
        sa.Column("passed", sa.Integer(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("recorded_at", sa.Text(), nullable=False),
    )
    op.create_index("ix_test_results_identifier", "test_results", ["identifier"])


def downgrade() -> None:
    op.drop_index("ix_test_results_identifier", table_name="test_results")
    op.drop_table("test_results")
    op.drop_index("ix_inspection_snapshots_identifier", table_name="inspection_snapshots")
    op.drop_table("inspection_snapshots")
