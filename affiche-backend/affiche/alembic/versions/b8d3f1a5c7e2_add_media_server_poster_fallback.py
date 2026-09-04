from alembic import op
import sqlalchemy as sa

revision = 'b8d3f1a5c7e2'
down_revision = 'a7c1e9d3b5f4'
branch_labels = None
depends_on = None

def _columns(table: str) -> set[str]:
    insp = sa.inspect(op.get_bind())
    return {col["name"] for col in insp.get_columns(table)}

def upgrade() -> None:
    existing = _columns('media_server')
    if 'fallback_to_server_poster' not in existing:
        op.add_column('media_server', sa.Column(
            'fallback_to_server_poster', sa.Boolean(), nullable=False,
            server_default=sa.false()))
    if 'skip_style_when_not_textless' not in existing:
        op.add_column('media_server', sa.Column(
            'skip_style_when_not_textless', sa.Boolean(), nullable=False,
            server_default=sa.false()))

def downgrade() -> None:
    with op.batch_alter_table('media_server') as batch_op:
        batch_op.drop_column('skip_style_when_not_textless')
        batch_op.drop_column('fallback_to_server_poster')
