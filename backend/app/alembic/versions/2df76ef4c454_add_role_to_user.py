"""add role to user

Revision ID: 2df76ef4c454
Revises: fe56fa70289e
Create Date: 2026-08-30 17:19:24.537414

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2df76ef4c454'
down_revision = 'fe56fa70289e'
branch_labels = None
depends_on = None


def upgrade():
    user_role = sa.Enum("admin", "manager", "member", name="userrole")
    user_role.create(op.get_bind())
    op.add_column(
        "user",
        sa.Column("role", user_role, nullable=False, server_default="member"),
    )
    # Existing superusers keep their privileges under the new role model
    op.execute("""UPDATE "user" SET role = 'admin' WHERE is_superuser = true""")


def downgrade():
    op.drop_column("user", "role")
    sa.Enum(name="userrole").drop(op.get_bind())
