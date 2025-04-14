"""rename_api_key_to_package_name

Revision ID: d67680cd6449
Revises: d6b7778d6d34
Create Date: 2025-04-13 14:57:02.806942

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'd67680cd6449'
down_revision = 'd6b7778d6d34'
branch_labels = None
depends_on = None


def upgrade():
    # Rename column api_key to package_name
    op.alter_column('application', 'api_key', new_column_name='package_name')


def downgrade():
    # Rename column package_name back to api_key
    op.alter_column('application', 'package_name', new_column_name='api_key')
