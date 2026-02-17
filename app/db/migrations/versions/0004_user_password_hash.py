"""add password hash to users"""

from alembic import op
import sqlalchemy as sa

revision = "0004_user_password_hash"
down_revision = "0003_monthly_locks"
branch_labels = None
depends_on = None

DEFAULT_ADMIN_HASH = "pbkdf2_sha256$120000$staticdefaultsalt0001$287aab5e5335ddafb1b2cd62285849a1806243c53ecc242e86bc9d29a75f9a91"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("users")}
    if "password_hash" not in cols:
        op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))

    op.execute(
        sa.text("UPDATE users SET password_hash = :h WHERE password_hash IS NULL OR password_hash = ''")
        .bindparams(h=DEFAULT_ADMIN_HASH)
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("users")}
    if "password_hash" in cols:
        op.drop_column("users", "password_hash")
