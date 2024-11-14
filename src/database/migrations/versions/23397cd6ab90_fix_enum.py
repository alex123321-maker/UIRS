from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '23397cd6ab90'
down_revision: Union[str, None] = 'f470e5ef1c6b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    new_enum = sa.Enum('HR', 'USER', name='roleenum')
    new_enum.create(op.get_bind())

    op.alter_column('users', 'role',
               existing_type=postgresql.ENUM('HR', 'USER', name='userrole'),
               type_=new_enum,
               existing_nullable=False,
               postgresql_using="role::text::roleenum")

    old_enum = postgresql.ENUM('HR', 'USER', name='userrole')
    old_enum.drop(op.get_bind())


def downgrade() -> None:
    old_enum = postgresql.ENUM('HR', 'USER', name='userrole')
    old_enum.create(op.get_bind())

    op.alter_column('users', 'role',
               existing_type=sa.Enum('HR', 'USER', name='roleenum'),
               type_=old_enum,
               existing_nullable=False,
               postgresql_using="role::text::userrole")

    new_enum = sa.Enum('HR', 'USER', name='roleenum')
    new_enum.drop(op.get_bind())
