from alembic import op
import sqlalchemy as sa

revision = 'f6a8b0c2d4e3'
down_revision = 'e5f7a9b1c3d2'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('library_item', sa.Column('poster_hash', sa.String(64), nullable=True))
    op.add_column('library_season', sa.Column('poster_hash', sa.String(64), nullable=True))

def downgrade() -> None:
    with op.batch_alter_table('library_season') as batch_op:
        batch_op.drop_column('poster_hash')
    with op.batch_alter_table('library_item') as batch_op:
        batch_op.drop_column('poster_hash')
