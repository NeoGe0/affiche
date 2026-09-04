from alembic import op
import sqlalchemy as sa

revision = 'b7d1f3a5c8e2'
down_revision = 'a2c4e6f8b1d3'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('library_item', sa.Column('style_hash', sa.String(64), nullable=True))
    op.add_column('library_season', sa.Column('style_hash', sa.String(64), nullable=True))

def downgrade() -> None:
    op.drop_column('library_season', 'style_hash')
    op.drop_column('library_item', 'style_hash')
