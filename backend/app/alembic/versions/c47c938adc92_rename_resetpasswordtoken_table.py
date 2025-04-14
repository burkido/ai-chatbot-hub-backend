"""rename_resetpasswordtoken_table

Revision ID: c47c938adc92
Revises: e2316ba26128
Create Date: 2025-04-13 19:41:17.607741

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'c47c938adc92'
down_revision = 'e2316ba26128'
branch_labels = None
depends_on = None


def upgrade():
    # Rename the table from 'resetpasswordtoken' to 'reset_password_token'
    op.rename_table('resetpasswordtoken', 'reset_password_token')
    
    # Rename the indexes to match the new table name
    op.execute('ALTER INDEX ix_resetpasswordtoken_application_id RENAME TO ix_reset_password_token_application_id')
    op.execute('ALTER INDEX ix_resetpasswordtoken_email RENAME TO ix_reset_password_token_email')
    op.execute('ALTER INDEX ix_resetpasswordtoken_user_id RENAME TO ix_reset_password_token_user_id')


def downgrade():
    # Rename everything back for downgrade
    op.execute('ALTER INDEX ix_reset_password_token_application_id RENAME TO ix_resetpasswordtoken_application_id')
    op.execute('ALTER INDEX ix_reset_password_token_email RENAME TO ix_resetpasswordtoken_email')
    op.execute('ALTER INDEX ix_reset_password_token_user_id RENAME TO ix_resetpasswordtoken_user_id')
    
    # Rename the table back to the original name
    op.rename_table('reset_password_token', 'resetpasswordtoken')
