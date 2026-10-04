from alembic import op
import sqlalchemy as sa

revision = 'c4f8b2e6a1d3'
down_revision = 'b7d9f1a3c5e8'
branch_labels = None
depends_on = None

_COLUMNS = ('tmdb_id_override', 'tmdb_season_number_override')

def _columns(table: str) -> set[str]:
    insp = sa.inspect(op.get_bind())
    return {col["name"] for col in insp.get_columns(table)}

def upgrade() -> None:
    existing = _columns('library_season')
    for column in _COLUMNS:
        if column not in existing:
            op.add_column('library_season', sa.Column(column, sa.Integer(), nullable=True))

def downgrade() -> None:
    existing = _columns('library_season')
    with op.batch_alter_table('library_season') as batch_op:
        for column in _COLUMNS:
            if column in existing:
                batch_op.drop_column(column)
