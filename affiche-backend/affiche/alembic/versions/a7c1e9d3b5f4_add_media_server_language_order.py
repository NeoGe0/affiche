import json

from alembic import op
import sqlalchemy as sa

from affiche.config.language_config import DEFAULT_LANGUAGE_ORDER

revision = 'a7c1e9d3b5f4'
down_revision = 'f6a8b0c2d4e3'
branch_labels = None
depends_on = None

def _columns(table: str) -> set[str]:
    insp = sa.inspect(op.get_bind())
    return {col["name"] for col in insp.get_columns(table)}

def upgrade() -> None:
    if 'language_order' in _columns('media_server'):
        return
    op.add_column('media_server', sa.Column(
        'language_order', sa.JSON(), nullable=False,
        server_default=sa.text(f"'{json.dumps(DEFAULT_LANGUAGE_ORDER)}'")))

def downgrade() -> None:
    with op.batch_alter_table('media_server') as batch_op:
        batch_op.drop_column('language_order')
