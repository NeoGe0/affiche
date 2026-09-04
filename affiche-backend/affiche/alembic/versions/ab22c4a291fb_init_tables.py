from alembic import op
import sqlalchemy as sa

revision = 'ab22c4a291fb'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('media_server',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('type', sa.Enum('PLEX', 'JELLYFIN', name='mediaservertype'), nullable=False),
    sa.Column('url', sa.String(length=1024), nullable=False),
    sa.Column('token', sa.String(length=1024), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('upload', sa.Boolean(), nullable=False),
    sa.Column('last_sync', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('service_configuration',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('type', sa.Enum('LIBRARY', 'PROVIDER', name='servicetype'), nullable=False),
    sa.Column('url', sa.String(length=1024), nullable=False),
    sa.Column('token', sa.String(length=1024), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('last_verified', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('library',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('media_server_id', sa.Integer(), nullable=False),
    sa.Column('external_id', sa.String(length=250), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('type', sa.String(length=100), nullable=False),
    sa.Column('item_count', sa.Integer(), nullable=False),
    sa.Column('agent', sa.String(length=100), nullable=True),
    sa.Column('language', sa.String(length=50), nullable=False),
    sa.Column('uuid', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['media_server_id'], ['media_server.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('external_id', 'media_server_id', name='uq_library_external_media_server')
    )
    op.create_table('library_item',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('external_id', sa.String(length=250), nullable=False),
    sa.Column('library_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=1024), nullable=False),
    sa.Column('type', sa.String(length=100), nullable=False),
    sa.Column('year', sa.Integer(), nullable=True),
    sa.Column('added_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('imdb_id', sa.String(length=150), nullable=True),
    sa.Column('tmdb_id', sa.String(length=150), nullable=True),
    sa.Column('tvdb_id', sa.String(length=150), nullable=True),
    sa.Column('poster_url', sa.String(length=2048), nullable=True),
    sa.Column('processed', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['library_id'], ['library.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('external_id', 'library_id', name='uq_library_item_external_library')
    )
    op.create_table('library_settings',
    sa.Column('library_id', sa.Integer(), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('upload_enabled', sa.Boolean(), nullable=False),
    sa.Column('provider_order', sa.JSON(), nullable=False),
    sa.Column('overlay_options', sa.JSON(), nullable=True),
    sa.Column('text_options', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['library_id'], ['library.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('library_id')
    )
    op.create_table('library_season',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('show_id', sa.Integer(), nullable=False),
    sa.Column('library_id', sa.Integer(), nullable=False),
    sa.Column('external_id', sa.String(length=250), nullable=False),
    sa.Column('season_number', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=1024), nullable=False),
    sa.Column('added_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('imdb_id', sa.String(length=150), nullable=True),
    sa.Column('tmdb_id', sa.String(length=150), nullable=True),
    sa.Column('tvdb_id', sa.String(length=150), nullable=True),
    sa.Column('poster_url', sa.String(length=2048), nullable=True),
    sa.Column('processed', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['library_id'], ['library.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['show_id'], ['library_item.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('external_id', 'show_id', 'library_id', name='uq_library_season_external_show_library')
    )

def downgrade() -> None:
    op.drop_table('library_season')
    op.drop_table('library_settings')
    op.drop_table('library_item')
    op.drop_table('library')
    op.drop_table('service_configuration')
    op.drop_table('media_server')
