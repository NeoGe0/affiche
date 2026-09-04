from alembic import op
import sqlalchemy as sa

revision = 'f4b8d2c6a9e1'
down_revision = 'e3a9c7b1d5f8'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'library_collection',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('external_id', sa.String(250), nullable=False),
        sa.Column('library_id', sa.Integer(),
                  sa.ForeignKey('library.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(1024), nullable=False),
        sa.Column('sort_title', sa.String(1024), nullable=True),
        sa.Column('child_count', sa.Integer(), nullable=True),
        sa.Column('added_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('poster_uploaded_at', sa.DateTime(), nullable=True),
        sa.Column('poster_url', sa.String(2048), nullable=True),
        sa.Column('poster_hash', sa.String(64), nullable=True),
        sa.Column('poster_provider', sa.String(50), nullable=True),
        sa.Column('processed', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('locked', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.UniqueConstraint('external_id', 'library_id',
                            name='uq_library_collection_external_library'),
    )

    op.create_table(
        'library_collection_item',
        sa.Column('collection_id', sa.Integer(),
                  sa.ForeignKey('library_collection.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('item_id', sa.Integer(),
                  sa.ForeignKey('library_item.id', ondelete='CASCADE'), primary_key=True),
    )

    op.add_column('library_settings',
                  sa.Column('track_collections', sa.Boolean(), nullable=False,
                            server_default=sa.false()))

def downgrade() -> None:
    with op.batch_alter_table('library_settings') as batch_op:
        batch_op.drop_column('track_collections')
    op.drop_table('library_collection_item')
    op.drop_table('library_collection')
