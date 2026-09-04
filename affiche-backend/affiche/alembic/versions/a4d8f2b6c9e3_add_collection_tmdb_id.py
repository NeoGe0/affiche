from alembic import op
import sqlalchemy as sa

revision = 'a4d8f2b6c9e3'
down_revision = 'f8a2c4e6b1d9'
branch_labels = None
depends_on = None

def _columns(table: str) -> set[str]:
    insp = sa.inspect(op.get_bind())
    return {col["name"] for col in insp.get_columns(table)}

def upgrade() -> None:
    if 'tmdb_collection_id' not in _columns('library_collection'):
        op.add_column('library_collection',
                      sa.Column('tmdb_collection_id', sa.Integer(), nullable=True))

def downgrade() -> None:
    if 'tmdb_collection_id' in _columns('library_collection'):
        with op.batch_alter_table('library_collection') as batch_op:
            batch_op.drop_column('tmdb_collection_id')
