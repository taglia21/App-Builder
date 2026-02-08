"""add role and is_demo_account to users

Revision ID: 20260207_demo_role
Revises: 
Create Date: 2026-02-07

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260207_demo_role'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add role column with default 'user'
    op.add_column('users', sa.Column('role', sa.String(20), nullable=False, server_default='user'))
    # Add is_demo_account column with default False
    op.add_column('users', sa.Column('is_demo_account', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('users', 'is_demo_account')
    op.drop_column('users', 'role')
