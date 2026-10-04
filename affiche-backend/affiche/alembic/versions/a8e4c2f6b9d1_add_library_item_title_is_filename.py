from alembic import op
import sqlalchemy as sa

revision = 'a8e4c2f6b9d1'
down_revision = 'c4f8b2e6a1d3'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('library_item',
                  sa.Column('title_is_filename', sa.Boolean(), nullable=False,
                            server_default=sa.false()))

def downgrade() -> None:
    with op.batch_alter_table('library_item') as batch_op:
        batch_op.drop_column('title_is_filename')
