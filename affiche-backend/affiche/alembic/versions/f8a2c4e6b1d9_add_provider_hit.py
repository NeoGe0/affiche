from alembic import op
import sqlalchemy as sa

revision = 'f8a2c4e6b1d9'
down_revision = 'a3c5e7b9d1f2'
branch_labels = None
depends_on = None

def upgrade() -> None:
    if 'provider_hit' in sa.inspect(op.get_bind()).get_table_names():
        return

    op.create_table(
        'provider_hit',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('library_id', sa.Integer(), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('day', 'provider', 'library_id',
                            name='uq_provider_hit_day_provider_library'),
    )
    op.create_index('ix_provider_hit_day', 'provider_hit', ['day'])

def downgrade() -> None:
    if 'provider_hit' in sa.inspect(op.get_bind()).get_table_names():
        op.drop_index('ix_provider_hit_day', table_name='provider_hit')
        op.drop_table('provider_hit')
