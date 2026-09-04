from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('library_settings', sa.Column(
        'auto_sync_enabled', sa.Boolean(), nullable=False, server_default=sa.text('0')))
    op.add_column('library_settings', sa.Column(
        'auto_sync_interval_minutes', sa.Integer(), nullable=False, server_default=sa.text('360')))
    op.add_column('library_settings', sa.Column(
        'auto_pickup_action', sa.String(length=20), nullable=False, server_default='sync'))
    op.add_column('library_settings', sa.Column(
        'last_auto_sync_at', sa.DateTime(), nullable=True))

def downgrade() -> None:
    with op.batch_alter_table('library_settings') as batch_op:
        batch_op.drop_column('last_auto_sync_at')
        batch_op.drop_column('auto_pickup_action')
        batch_op.drop_column('auto_sync_interval_minutes')
        batch_op.drop_column('auto_sync_enabled')
