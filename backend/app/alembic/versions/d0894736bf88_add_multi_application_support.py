"""Add multi-application support

Revision ID: d0894736bf88
Revises: 31ce95dd3862
Create Date: 2025-04-11 12:11:45.188063

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy.dialects import postgresql
import uuid

from app.models.database.application import Application

# revision identifiers, used by Alembic.
revision = 'd0894736bf88'
down_revision = '31ce95dd3862'
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Create the application table first
    op.create_table(
        'application',
        sa.Column('id', postgresql.UUID(), nullable=False, primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('api_key', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('default_user_credit', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('deeplink_base_url', sa.String(255), nullable=False, server_default='https://example.com'),
    )
    
    # Step 2: Create a default application to associate with existing users
    # Using a random UUID and a simple base64 string as API key
    default_app_id = str(uuid.uuid4())
    default_api_key = 'default_api_key_' + str(uuid.uuid4()).replace('-', '')
    op.execute(
        f"""
        INSERT INTO application (
            id, name, api_key, description, is_active
        ) VALUES (
            '{default_app_id}', 'Default Application', 
            '{default_api_key}', 
            'Default application created during migration', 
            true
        )
        """
    )
    
    # Force a transaction commit to ensure the application table is fully created
    # before we reference it in foreign keys
    op.execute("COMMIT")
    
    # Step 3: Add application_id column to user table
    op.add_column(
        'user', 
        sa.Column('application_id', postgresql.UUID(), nullable=True)
    )
    
    # Step 4: Associate existing users with the default application
    op.execute(
        f"""
        UPDATE "user" 
        SET application_id = '{default_app_id}'
        WHERE application_id IS NULL
        """
    )
    
    # Step 5: Now make the application_id column not nullable
    op.alter_column('user', 'application_id', nullable=False)
    
    # Step 6: Add foreign key constraint to user.application_id
    op.create_foreign_key(
        'user_application_id_fkey', 
        'user', 'application', 
        ['application_id'], ['id']
    )

    # Step 7: Remove the unique constraint from user.email
    # First identify the existing constraint name
    op.execute(
        """
        DO $$
        DECLARE
            constraint_name varchar;
        BEGIN
            SELECT conname INTO constraint_name
            FROM pg_constraint
            JOIN pg_class ON pg_constraint.conrelid = pg_class.oid
            WHERE pg_class.relname = 'user' AND contype = 'u' AND conkey @> ARRAY[2::smallint];
            
            IF constraint_name IS NOT NULL THEN
                EXECUTE 'ALTER TABLE "user" DROP CONSTRAINT ' || constraint_name;
            END IF;
        END $$;
        """
    )
    
    # Step 8: Add composite unique constraint for application_id + email
    op.create_unique_constraint(
        'uix_user_application_email', 
        'user', 
        ['application_id', 'email']
    )
    
    # Step 9: Add application_id to the invitation table
    op.add_column(
        'invitation', 
        sa.Column('application_id', postgresql.UUID(), nullable=True)
    )
    
    # Step 10: Associate existing invitations with the default application
    op.execute(
        f"""
        UPDATE invitation 
        SET application_id = '{default_app_id}'
        WHERE application_id IS NULL
        """
    )
    
    # Step 11: Now make the application_id column not nullable
    op.alter_column('invitation', 'application_id', nullable=False)
    
    # Step 12: Add foreign key constraint to invitation.application_id
    op.create_foreign_key(
        'invitation_application_id_fkey', 
        'invitation', 'application', 
        ['application_id'], ['id']
    )
    
    # Step 13: Add application_id to otp table
    op.add_column(
        'otp', 
        sa.Column('application_id', postgresql.UUID(), nullable=True)
    )
    
    # Step 14: Associate existing OTPs with the default application
    op.execute(
        f"""
        UPDATE otp 
        SET application_id = '{default_app_id}'
        WHERE application_id IS NULL
        """
    )
    
    # Step 15: Make the application_id column not nullable
    op.alter_column('otp', 'application_id', nullable=False)
    
    # Step 16: Add foreign key constraint to otp.application_id
    op.create_foreign_key(
        'otp_application_id_fkey', 
        'otp', 'application', 
        ['application_id'], ['id']
    )


def downgrade():
    # Remove the application-specific constraints and columns in reverse order
    
    # Remove foreign key constraint and column from otp
    op.drop_constraint('otp_application_id_fkey', 'otp', type_='foreignkey')
    op.drop_column('otp', 'application_id')
    
    # Remove foreign key constraint and column from invitation
    op.drop_constraint('invitation_application_id_fkey', 'invitation', type_='foreignkey')
    op.drop_column('invitation', 'application_id')
    
    # Restore original email uniqueness and remove application association from user
    op.drop_constraint('uix_user_application_email', 'user', type_='unique')
    op.create_unique_constraint('user_email_key', 'user', ['email'])
    op.drop_constraint('user_application_id_fkey', 'user', type_='foreignkey')
    op.drop_column('user', 'application_id')
    
    # Drop the application table last
    op.drop_table('application')
