from alembic import op
import sqlalchemy as sa

revision = 'f3b5c7d9e1a2'
down_revision = 'e2a7c9d4f6b1'
branch_labels = None
depends_on = None

_COLUMN = sa.Column('release_date', sa.DateTime(), nullable=True)

def upgrade() -> None:
    op.add_column('library_item', _COLUMN)

def downgrade() -> None:
    with op.batch_alter_table('library_item') as batch_op:
        batch_op.drop_column('release_date')
