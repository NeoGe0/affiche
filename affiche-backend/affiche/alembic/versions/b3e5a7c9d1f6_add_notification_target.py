from alembic import op
import sqlalchemy as sa

from affiche.app.encryption.encryption import EncryptedString
from affiche.config.env_config import get_encryption_key

revision = 'b3e5a7c9d1f6'
down_revision = 'a5c7e9b3d1f4'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'notification_target',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('type', sa.Enum('DISCORD', 'GOTIFY', 'APPRISE', 'WEBHOOK',
                                  name='notificationtype'), nullable=False),
        sa.Column('url', EncryptedString(key_provider=get_encryption_key), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('on_task_completed', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('on_task_failed', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('on_items_errored', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

def downgrade() -> None:
    op.drop_table('notification_target')
