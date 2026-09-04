from alembic import op
import sqlalchemy as sa

revision = 'c1e5a7b9d3f6'
down_revision = 'b8d3f1a5c7e2'
branch_labels = None
depends_on = None

def _columns(table: str) -> set[str]:
    insp = sa.inspect(op.get_bind())
    return {col["name"] for col in insp.get_columns(table)}

def upgrade() -> None:
    if 'upload' in _columns('media_server'):
        with op.batch_alter_table('media_server') as batch_op:
            batch_op.drop_column('upload')

def downgrade() -> None:
    if 'upload' not in _columns('media_server'):
        op.add_column('media_server', sa.Column(
            'upload', sa.Boolean(), nullable=False, server_default=sa.true()))
