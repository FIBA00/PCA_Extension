"""add prompt status

Revision ID: c5e6f7g8h9i0
Revises: b4d5e6f7g8h9
Create Date: 2026-02-10 16:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c5e6f7g8h9i0"
down_revision: Union[str, Sequence[str], None] = "b4d5e6f7g8h9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('structured_prompts', sa.Column('status', sa.String(), nullable=True, server_default='PENDING'))
    op.add_column('structured_prompts', sa.Column('error_message', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('structured_prompts', 'status')
    op.drop_column('structured_prompts', 'error_message')
