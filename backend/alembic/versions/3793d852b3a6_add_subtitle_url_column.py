"""add_subtitle_url_column

Revision ID: 3793d852b3a6
Revises: 3c52053ec023
Create Date: 2025-02-06 17:33:34.700388

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3793d852b3a6'
down_revision: Union[str, None] = '3c52053ec023'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('messages', sa.Column('subtitle_url', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('messages', 'subtitle_url')
    # ### end Alembic commands ###
