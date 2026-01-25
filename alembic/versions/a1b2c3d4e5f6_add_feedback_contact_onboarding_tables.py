"""Add Feedback, ContactSubmission, and OnboardingStatus tables

Revision ID: a1b2c3d4e5f6
Revises: ef2c9ca2bc1b
Create Date: 2026-01-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Text
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'ef2c9ca2bc1b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Feedback, ContactSubmission, and OnboardingStatus tables."""
    
    # Create Feedback table
    op.create_table('feedback',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=True),  # Optional - anonymous feedback allowed
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('category', sa.Enum('general', 'bug', 'feature', 'improvement', name='feedbackcategory'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'reviewed', 'resolved', 'archived', name='feedbackstatus'), nullable=False, server_default='pending'),
        sa.Column('page_url', sa.String(500), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_feedback_user_id', 'feedback', ['user_id'], unique=False)
    op.create_index('idx_feedback_status', 'feedback', ['status'], unique=False)
    op.create_index('idx_feedback_category', 'feedback', ['category'], unique=False)
    op.create_index('idx_feedback_created_at', 'feedback', ['created_at'], unique=False)
    
    # Create ContactSubmission table
    op.create_table('contact_submissions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=True),  # Optional - if logged in
        sa.Column('status', sa.Enum('pending', 'replied', 'resolved', 'spam', name='contactstatus'), nullable=False, server_default='pending'),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.Column('replied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reply_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_contact_email', 'contact_submissions', ['email'], unique=False)
    op.create_index('idx_contact_status', 'contact_submissions', ['status'], unique=False)
    op.create_index('idx_contact_created_at', 'contact_submissions', ['created_at'], unique=False)
    op.create_index('idx_contact_user_id', 'contact_submissions', ['user_id'], unique=False)
    
    # Create OnboardingStatus table
    op.create_table('onboarding_status',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('api_keys_set', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('first_app_generated', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('first_deploy_completed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('api_keys_set_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('first_app_generated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('first_deploy_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_onboarding_user_id')
    )
    op.create_index('idx_onboarding_user_id', 'onboarding_status', ['user_id'], unique=True)


def downgrade() -> None:
    """Remove Feedback, ContactSubmission, and OnboardingStatus tables."""
    
    # Drop OnboardingStatus table
    op.drop_index('idx_onboarding_user_id', table_name='onboarding_status')
    op.drop_table('onboarding_status')
    
    # Drop ContactSubmission table
    op.drop_index('idx_contact_user_id', table_name='contact_submissions')
    op.drop_index('idx_contact_created_at', table_name='contact_submissions')
    op.drop_index('idx_contact_status', table_name='contact_submissions')
    op.drop_index('idx_contact_email', table_name='contact_submissions')
    op.drop_table('contact_submissions')
    
    # Drop Feedback table
    op.drop_index('idx_feedback_created_at', table_name='feedback')
    op.drop_index('idx_feedback_category', table_name='feedback')
    op.drop_index('idx_feedback_status', table_name='feedback')
    op.drop_index('idx_feedback_user_id', table_name='feedback')
    op.drop_table('feedback')
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS feedbackcategory")
    op.execute("DROP TYPE IF EXISTS feedbackstatus")
    op.execute("DROP TYPE IF EXISTS contactstatus")
