"""Recovered migration

Revision ID: 7204bb193797
Revises: 9b1529955588
Create Date: $(date -u +"%Y-%m-%d %H:%M:%S")

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes

# revision identifiers, used by Alembic.
revision = '7204bb193797'
down_revision = '9b1529955588'
branch_labels = None
depends_on = None


def upgrade():
    # This is a recovered empty migration to fix the missing migration issue
    pass


def downgrade():
    # This is a recovered empty migration to fix the missing migration issue
    pass
