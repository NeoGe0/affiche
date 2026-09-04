from alembic import op
import sqlalchemy as sa

revision = 'b7d2e4f1a3c5'
down_revision = 'ab22c4a291fb'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('library_item', sa.Column('last_seen_at', sa.DateTime(), nullable=True))
    op.add_column('library_item', sa.Column('poster_uploaded_at', sa.DateTime(), nullable=True))

def downgrade() -> None:
    with op.batch_alter_table('library_item') as batch_op:
        batch_op.drop_column('poster_uploaded_at')
        batch_op.drop_column('last_seen_at')
