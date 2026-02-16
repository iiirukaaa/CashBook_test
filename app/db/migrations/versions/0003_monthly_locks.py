"""monthly lock table"""

from alembic import op
import sqlalchemy as sa

revision = "0003_monthly_locks"
down_revision = "0002_monthly_balance_per_account"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "monthly_locks" in inspector.get_table_names():
        return
    op.create_table(
        "monthly_locks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("is_locked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("year", "month", name="uq_monthly_lock"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "monthly_locks" in inspector.get_table_names():
        op.drop_table("monthly_locks")
