from alembic import op
import sqlalchemy as sa

revision = 'e2a7c9d4f6b1'
down_revision = 'd1f4a6b8c2e9'
branch_labels = None
depends_on = None

_COLUMNS = (
    sa.Column('media_resolution', sa.String(length=20), nullable=True),
    sa.Column('media_width', sa.Integer(), nullable=True),
    sa.Column('media_height', sa.Integer(), nullable=True),
    sa.Column('video_codec', sa.String(length=50), nullable=True),
    sa.Column('audio_codec', sa.String(length=50), nullable=True),
    sa.Column('audio_channels', sa.Integer(), nullable=True),
    sa.Column('media_container', sa.String(length=50), nullable=True),
    sa.Column('media_bitrate', sa.Integer(), nullable=True),
    sa.Column('media_size_bytes', sa.BigInteger(), nullable=True),
)

def upgrade() -> None:
    for column in _COLUMNS:
        op.add_column('library_item', column)

def downgrade() -> None:
    with op.batch_alter_table('library_item') as batch_op:
        for column in _COLUMNS:
            batch_op.drop_column(column.name)
