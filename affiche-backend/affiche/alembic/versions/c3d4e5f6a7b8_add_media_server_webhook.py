from alembic import op
import sqlalchemy as sa

revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None

def _columns(table: str) -> set[str]:
    insp = sa.inspect(op.get_bind())
    return {col["name"] for col in insp.get_columns(table)}

def _indexes(table: str) -> set[str]:
    insp = sa.inspect(op.get_bind())
    return {idx["name"] for idx in insp.get_indexes(table)}

def upgrade() -> None:
    existing = _columns('media_server')
    if 'webhook_enabled' not in existing:
        op.add_column('media_server', sa.Column(
            'webhook_enabled', sa.Boolean(), nullable=False, server_default=sa.text('0')))
    if 'webhook_token' not in existing:
        op.add_column('media_server', sa.Column(
            'webhook_token', sa.String(length=64), nullable=True))
    if 'uq_media_server_webhook_token' not in _indexes('media_server'):
        op.create_index('uq_media_server_webhook_token', 'media_server',
                        ['webhook_token'], unique=True)

def downgrade() -> None:
    if 'uq_media_server_webhook_token' in _indexes('media_server'):
        op.drop_index('uq_media_server_webhook_token', table_name='media_server')
    with op.batch_alter_table('media_server') as batch_op:
        batch_op.drop_column('webhook_token')
        batch_op.drop_column('webhook_enabled')
