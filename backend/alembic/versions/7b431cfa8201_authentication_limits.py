"""Shared authentication attempt limits."""
from alembic import op
import sqlalchemy as sa

revision = '7b431cfa8201'
down_revision = '1a8fa6568233'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('auth_rate_limits',
                    sa.Column('bucket_key', sa.String(64), primary_key=True),
                    sa.Column('expires_at', sa.BigInteger(), nullable=False),
                    sa.Column('attempts', sa.Integer(), nullable=False))
    op.create_index('ix_auth_rate_limits_expires_at', 'auth_rate_limits', ['expires_at'])


def downgrade():
    op.drop_index('ix_auth_rate_limits_expires_at', table_name='auth_rate_limits')
    op.drop_table('auth_rate_limits')
