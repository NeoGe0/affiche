from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = 'd7b3e9a1c5f2'
down_revision = 'c2a6e8b4d7f1'
branch_labels = None
depends_on = None

def _columns(table: str) -> set[str]:
    insp = sa.inspect(op.get_bind())
    return {col["name"] for col in insp.get_columns(table)}

def upgrade() -> None:
    if 'poster_uploaded_at' in _columns('library_season'):
        return
    op.add_column('library_season', sa.Column('poster_uploaded_at', sa.DateTime(), nullable=True))

    season = sa.table('library_season',
                      sa.column('poster_hash', sa.String),
                      sa.column('poster_uploaded_at', sa.DateTime))
    op.execute(season.update()
               .where(season.c.poster_hash.is_not(None))
               .values(poster_uploaded_at=datetime.now(timezone.utc)))

def downgrade() -> None:
    if 'poster_uploaded_at' in _columns('library_season'):
        with op.batch_alter_table('library_season') as batch_op:
            batch_op.drop_column('poster_uploaded_at')
