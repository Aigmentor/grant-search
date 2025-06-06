"""Add index

Revision ID: 2796a449b927
Revises: 6188e173690f
Create Date: 2024-12-15 20:44:06.958547

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2796a449b927'
down_revision: Union[str, None] = '6188e173690f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index('idx_grant_search_queries_user_id', 'grant_search_queries', ['user_id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('idx_grant_search_queries_user_id', table_name='grant_search_queries')
    # ### end Alembic commands ###
