from alembic import op
import sqlalchemy as sa

revision = 'd1f4a6b8c2e9'
down_revision = 'c9e3f5a2b1d7'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('library_item', sa.Column('error_message', sa.Text(), nullable=True))

def downgrade() -> None:
    with op.batch_alter_table('library_item') as batch_op:
        batch_op.drop_column('error_message')
