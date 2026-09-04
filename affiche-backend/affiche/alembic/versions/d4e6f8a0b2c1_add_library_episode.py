from alembic import op
import sqlalchemy as sa

revision = 'd4e6f8a0b2c1'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'library_episode',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('season_id', sa.Integer(), nullable=False),
        sa.Column('show_id', sa.Integer(), nullable=False),
        sa.Column('library_id', sa.Integer(), nullable=False),
        sa.Column('external_id', sa.String(length=250), nullable=False),
        sa.Column('season_number', sa.Integer(), nullable=False),
        sa.Column('episode_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=1024), nullable=False),
        sa.Column('air_date', sa.DateTime(), nullable=True),
        sa.Column('added_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('imdb_id', sa.String(length=150), nullable=True),
        sa.Column('tmdb_id', sa.String(length=150), nullable=True),
        sa.Column('tvdb_id', sa.String(length=150), nullable=True),
        sa.Column('media_resolution', sa.String(length=20), nullable=True),
        sa.Column('media_width', sa.Integer(), nullable=True),
        sa.Column('media_height', sa.Integer(), nullable=True),
        sa.Column('video_codec', sa.String(length=50), nullable=True),
        sa.Column('audio_codec', sa.String(length=50), nullable=True),
        sa.Column('audio_channels', sa.Integer(), nullable=True),
        sa.Column('media_container', sa.String(length=50), nullable=True),
        sa.Column('media_bitrate', sa.Integer(), nullable=True),
        sa.Column('media_size_bytes', sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(['season_id'], ['library_season.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['show_id'], ['library_item.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['library_id'], ['library.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_id', 'season_id', 'library_id',
                            name='uq_library_episode_external_season_library'),
    )

def downgrade() -> None:
    op.drop_table('library_episode')
