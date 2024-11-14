"""Update role to enum in User model

Revision ID: f470e5ef1c6b
Revises: 1b40212d02c2
Create Date: 2024-11-14 13:45:21.065609

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f470e5ef1c6b'
down_revision: Union[str, None] = '1b40212d02c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('users_role_id_fkey', 'users', type_='foreignkey')
    op.drop_column('users', 'role_id')

    user_role_enum = sa.Enum('HR', 'USER', name='userrole')
    user_role_enum.create(op.get_bind())

    op.add_column('users', sa.Column('role', user_role_enum, nullable=False))

    op.drop_index('ix_roles_id', table_name='roles')
    op.drop_index('ix_roles_name', table_name='roles')
    op.drop_table('roles')


def downgrade() -> None:
    op.create_table('roles',
                    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
                    sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=True),
                    sa.PrimaryKeyConstraint('id', name='roles_pkey')
                    )
    op.create_index('ix_roles_name', 'roles', ['name'], unique=True)
    op.create_index('ix_roles_id', 'roles', ['id'], unique=False)

    op.add_column('users', sa.Column('role_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key('users_role_id_fkey', 'users', 'roles', ['role_id'], ['id'])

    op.drop_column('users', 'role')
    user_role_enum = sa.Enum('HR', 'USER', name='userrole')
    user_role_enum.drop(op.get_bind())