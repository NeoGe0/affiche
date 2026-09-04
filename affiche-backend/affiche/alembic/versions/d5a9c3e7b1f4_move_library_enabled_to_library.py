from alembic import op
import sqlalchemy as sa

revision = 'd5a9c3e7b1f4'
down_revision = 'b3e5a7c9d1f6'
branch_labels = None
depends_on = None

def _columns(table: str) -> set[str]:
    insp = sa.inspect(op.get_bind())
    return {col["name"] for col in insp.get_columns(table)}

def upgrade() -> None:
    if 'enabled' not in _columns('library_settings'):
        return

    op.execute(sa.text("""
        UPDATE library
           SET enabled = COALESCE(
                 (SELECT ls.enabled FROM library_settings ls WHERE ls.library_id = library.id),
                 library.enabled)
    """))

    with op.batch_alter_table('library_settings') as batch_op:
        batch_op.drop_column('enabled')

def downgrade() -> None:
    if 'enabled' in _columns('library_settings'):
        return

    op.add_column('library_settings', sa.Column(
        'enabled', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.execute(sa.text("""
        UPDATE library_settings
           SET enabled = COALESCE(
                 (SELECT l.enabled FROM library l WHERE l.id = library_settings.library_id),
                 1)
    """))
