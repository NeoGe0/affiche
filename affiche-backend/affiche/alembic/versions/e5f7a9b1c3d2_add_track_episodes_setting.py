from alembic import op
import sqlalchemy as sa

revision = 'e5f7a9b1c3d2'
down_revision = 'd4e6f8a0b2c1'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('library_settings', sa.Column(
        'track_episodes', sa.Boolean(), nullable=False, server_default=sa.text('0')))

def downgrade() -> None:
    with op.batch_alter_table('library_settings') as batch_op:
        batch_op.drop_column('track_episodes')
