from alembic import op
import sqlalchemy as sa

revision = 'b7d9f1a3c5e8'
down_revision = 'e1a3c5d7f9b2'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('library_item', sa.Column('poster_generated_at', sa.DateTime(), nullable=True))

def downgrade() -> None:
    with op.batch_alter_table('library_item') as batch_op:
        batch_op.drop_column('poster_generated_at')
