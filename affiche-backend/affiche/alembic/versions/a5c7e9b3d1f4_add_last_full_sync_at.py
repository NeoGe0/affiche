from alembic import op
import sqlalchemy as sa

revision = 'a5c7e9b3d1f4'
down_revision = 'a4d8f2b6c9e3'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('library_settings',
                  sa.Column('last_full_sync_at', sa.DateTime(), nullable=True))

def downgrade() -> None:
    with op.batch_alter_table('library_settings') as batch_op:
        batch_op.drop_column('last_full_sync_at')
