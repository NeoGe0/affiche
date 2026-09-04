from alembic import op
import sqlalchemy as sa

revision = 'a3c5e7b9d1f2'
down_revision = 'f2b4d6a8c1e5'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column(
        'user',
        sa.Column('role', sa.Enum('ADMIN', 'OPERATOR', name='userrole'),
                  nullable=False, server_default='ADMIN'),
    )

def downgrade() -> None:
    op.drop_column('user', 'role')
