from alembic import op
import sqlalchemy as sa

revision = 'b9f3d5a7c2e4'
down_revision = 'a8e4c2f6b9d1'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('library_item',
                  sa.Column('title_mismatched', sa.Boolean(), nullable=False,
                            server_default=sa.false()))
    op.add_column('library_item', sa.Column('title_checked_at', sa.DateTime(), nullable=True))
    with op.batch_alter_table('library_item') as batch_op:
        batch_op.drop_column('title_is_filename')

def downgrade() -> None:
    op.add_column('library_item',
                  sa.Column('title_is_filename', sa.Boolean(), nullable=False,
                            server_default=sa.false()))
    with op.batch_alter_table('library_item') as batch_op:
        batch_op.drop_column('title_checked_at')
        batch_op.drop_column('title_mismatched')
