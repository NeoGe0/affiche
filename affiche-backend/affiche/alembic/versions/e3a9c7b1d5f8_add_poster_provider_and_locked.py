from alembic import op
import sqlalchemy as sa

revision = 'e3a9c7b1d5f8'
down_revision = 'd2f6b8a4c1e3'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('library_item', sa.Column('poster_provider', sa.String(50), nullable=True))
    op.add_column('library_season', sa.Column('poster_provider', sa.String(50), nullable=True))
    op.add_column('library_item', sa.Column('locked', sa.Boolean(), nullable=False,
                                            server_default=sa.false()))

def downgrade() -> None:
    with op.batch_alter_table('library_item') as batch_op:
        batch_op.drop_column('locked')
        batch_op.drop_column('poster_provider')
    with op.batch_alter_table('library_season') as batch_op:
        batch_op.drop_column('poster_provider')
