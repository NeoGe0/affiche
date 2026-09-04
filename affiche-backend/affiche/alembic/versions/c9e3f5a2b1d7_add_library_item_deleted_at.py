from alembic import op
import sqlalchemy as sa

revision = 'c9e3f5a2b1d7'
down_revision = 'b7d2e4f1a3c5'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('library_item', sa.Column('deleted_at', sa.DateTime(), nullable=True))

def downgrade() -> None:
    with op.batch_alter_table('library_item') as batch_op:
        batch_op.drop_column('deleted_at')
