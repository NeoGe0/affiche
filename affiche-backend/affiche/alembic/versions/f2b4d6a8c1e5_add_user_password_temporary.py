from alembic import op
import sqlalchemy as sa

revision = 'f2b4d6a8c1e5'
down_revision = 'e7c3a1f5b9d2'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column(
        'user',
        sa.Column('password_temporary', sa.Boolean(), nullable=False, server_default='0'),
    )

def downgrade() -> None:
    op.drop_column('user', 'password_temporary')
