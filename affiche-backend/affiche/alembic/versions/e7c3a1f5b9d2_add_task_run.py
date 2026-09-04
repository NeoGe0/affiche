from alembic import op
import sqlalchemy as sa

revision = 'e7c3a1f5b9d2'
down_revision = 'd3f7b1c5a9e4'
branch_labels = None
depends_on = None

def upgrade() -> None:
    if 'task_run' in sa.inspect(op.get_bind()).get_table_names():
        return

    op.create_table(
        'task_run',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.String(length=64), nullable=False),
        sa.Column('task_name', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('resource', sa.String(length=100), nullable=True),
        sa.Column('media_server_id', sa.Integer(), nullable=True),
        sa.Column('library_id', sa.Integer(), nullable=True),
        sa.Column('blocking', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('items_done', sa.Integer(), nullable=True),
        sa.Column('items_total', sa.Integer(), nullable=True),
        sa.Column('message', sa.String(length=500), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id', name='uq_task_run_task_id'),
    )
    op.create_index('ix_task_run_created_at', 'task_run', ['created_at'])
    op.create_index('ix_task_run_task_id', 'task_run', ['task_id'])

def downgrade() -> None:
    if 'task_run' in sa.inspect(op.get_bind()).get_table_names():
        op.drop_index('ix_task_run_task_id', table_name='task_run')
        op.drop_index('ix_task_run_created_at', table_name='task_run')
        op.drop_table('task_run')
