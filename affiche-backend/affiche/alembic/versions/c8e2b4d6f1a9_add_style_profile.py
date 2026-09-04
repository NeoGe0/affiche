from alembic import op
import sqlalchemy as sa

revision = 'c8e2b4d6f1a9'
down_revision = 'b7d1f3a5c8e2'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'style_profile',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('overlay_options', sa.JSON(), nullable=True),
        sa.Column('text_options', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_style_profile_name', 'style_profile', ['name'], unique=True)

    with op.batch_alter_table('library_settings') as batch:
        batch.add_column(sa.Column('style_profile_id', sa.Integer(), nullable=True))
        batch.create_foreign_key(
            'fk_library_settings_style_profile', 'style_profile',
            ['style_profile_id'], ['id'], ondelete='SET NULL')

def downgrade() -> None:
    with op.batch_alter_table('library_settings') as batch:
        batch.drop_constraint('fk_library_settings_style_profile', type_='foreignkey')
        batch.drop_column('style_profile_id')

    op.drop_index('ix_style_profile_name', table_name='style_profile')
    op.drop_table('style_profile')
