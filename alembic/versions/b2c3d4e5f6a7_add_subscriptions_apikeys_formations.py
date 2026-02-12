"""Add subscriptions, api_keys, and business_formations tables

Revision ID: b2c3d4e5f6a7
Revises: 20260207_demo_role
Create Date: 2026-02-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = '20260207_demo_role'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- subscriptions ---
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('stripe_customer_id', sa.String(255), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(255), nullable=True),
        sa.Column('stripe_price_id', sa.String(255), nullable=True),
        sa.Column('tier', sa.Enum('free', 'starter', 'pro', 'enterprise', name='subscriptiontier'), default='free'),
        sa.Column('status', sa.Enum('active', 'canceled', 'past_due', 'trialing', 'paused', name='subscriptionstatus'), default='active'),
        sa.Column('app_generations_limit', sa.Integer(), default=1),
        sa.Column('app_generations_used', sa.Integer(), default=0),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- api_keys ---
    op.create_table(
        'api_keys',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('key_hash', sa.String(255), nullable=False),
        sa.Column('key_prefix', sa.String(10), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('rate_limit', sa.Integer(), default=1000),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_requests', sa.Integer(), default=0),
        sa.Column('is_deleted', sa.Boolean(), default=False, nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- business_formations ---
    op.create_table(
        'business_formations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('business_name', sa.String(255), nullable=False),
        sa.Column('business_type', sa.String(50), default='LLC'),
        sa.Column('state', sa.String(2), nullable=False),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('ein_number', sa.String(20), nullable=True),
        sa.Column('formation_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('external_order_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- credit_transactions (new — persists credit operations) ---
    op.create_table(
        'credit_transactions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('balance_after', sa.Integer(), nullable=False),
        sa.Column('transaction_type', sa.String(50), nullable=False),  # credit, debit, refund, grant
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('reference_id', sa.String(255), nullable=True),  # e.g. project_id, subscription_id
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_credit_transactions_user', 'credit_transactions', ['user_id'])
    op.create_index('idx_credit_transactions_type', 'credit_transactions', ['transaction_type'])

    # --- webhook_events (idempotency/audit trail) ---
    op.create_table(
        'webhook_events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('stripe_event_id', sa.String(255), unique=True, nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('processed', sa.Boolean(), default=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_webhook_events_stripe_id', 'webhook_events', ['stripe_event_id'])


def downgrade() -> None:
    op.drop_table('webhook_events')
    op.drop_table('credit_transactions')
    op.drop_table('business_formations')
    op.drop_table('api_keys')
    op.drop_table('subscriptions')
