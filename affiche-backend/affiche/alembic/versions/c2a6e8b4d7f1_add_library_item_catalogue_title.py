from alembic import op
import sqlalchemy as sa

revision = 'c2a6e8b4d7f1'
down_revision = 'b9f3d5a7c2e4'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('library_item',
                  sa.Column('catalogue_title', sa.String(length=1024), nullable=True))
    op.add_column('library_item',
                  sa.Column('catalogue_provider', sa.String(length=50), nullable=True))

def downgrade() -> None:
    with op.batch_alter_table('library_item') as batch_op:
        batch_op.drop_column('catalogue_provider')
        batch_op.drop_column('catalogue_title')
