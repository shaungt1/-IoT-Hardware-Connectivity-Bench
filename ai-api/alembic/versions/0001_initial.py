"""Create local bench state tables."""

from alembic import op
import sqlalchemy as sa


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("settings", sa.Column("key", sa.Text(), primary_key=True), sa.Column("value", sa.Text(), nullable=False))
    op.create_table(
        "connection_profiles",
        sa.Column("port", sa.Text(), primary_key=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("manufacturer", sa.Text()),
        sa.Column("serial_number", sa.Text()),
        sa.Column("vid", sa.Text()),
        sa.Column("pid", sa.Text()),
        sa.Column("is_esp32", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("last_connected_at", sa.Text(), nullable=False),
    )
    op.create_table(
        "wireless_profiles",
        sa.Column("kind", sa.Text(), primary_key=True),
        sa.Column("identifier", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("metadata", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("last_connected_at", sa.Text(), nullable=False),
    )
    op.create_table(
        "operation_audit",
        sa.Column("sequence", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("plan_id", sa.Text(), nullable=False),
        sa.Column("identifier", sa.Text(), nullable=False),
        sa.Column("operation_id", sa.Text(), nullable=False),
        sa.Column("risk", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("preview", sa.Text(), nullable=False),
        sa.Column("output", sa.Text(), nullable=False),
        sa.Column("recorded_at", sa.Text(), nullable=False),
    )
    op.create_table(
        "prototype_projects",
        sa.Column("identifier", sa.Text(), primary_key=True),
        sa.Column("schema_version", sa.Text(), nullable=False),
        sa.Column("project_json", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("prototype_projects")
    op.drop_table("operation_audit")
    op.drop_table("wireless_profiles")
    op.drop_table("connection_profiles")
    op.drop_table("settings")
