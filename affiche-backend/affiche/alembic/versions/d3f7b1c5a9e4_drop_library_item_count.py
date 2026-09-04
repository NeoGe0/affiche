from alembic import op
import sqlalchemy as sa

revision = 'd3f7b1c5a9e4'
down_revision = 'c8e2b4d6f1a9'
branch_labels = None
depends_on = None

def _columns(table: str) -> set[str]:
    insp = sa.inspect(op.get_bind())
    return {col["name"] for col in insp.get_columns(table)}

def upgrade() -> None:
    if 'item_count' in _columns('library'):
        with op.batch_alter_table('library') as batch_op:
            batch_op.drop_column('item_count')

def downgrade() -> None:
    if 'item_count' not in _columns('library'):
        op.add_column('library', sa.Column(
            'item_count', sa.Integer(), nullable=False, server_default='0'))
