"""restore_email_unique_constraint

Revision ID: f3965c8d1b61
Revises: ec9f8d110608
Create Date: 2025-04-14 11:54:46.569709

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'f3965c8d1b61'
down_revision = 'ec9f8d110608'
branch_labels = None
depends_on = None


def upgrade():
    # First, handle duplicate emails by appending a suffix to duplicates
    # This keeps all your data while ensuring uniqueness
    conn = op.get_bind()
    
    # Find duplicate emails
    find_duplicates_query = text('''
        SELECT email 
        FROM "user" 
        GROUP BY email 
        HAVING COUNT(*) > 1
    ''')
    
    # For each duplicate email, keep the first one as is and append a suffix to others
    for row in conn.execute(find_duplicates_query):
        duplicate_email = row[0]
        
        # Get all user IDs with this email, ordered by creation date (assuming first record is the one to keep)
        user_ids_query = text('''
            SELECT id 
            FROM "user" 
            WHERE email = :email 
            ORDER BY id
        ''')
        
        # Execute the query with the duplicate email as parameter
        user_ids = [str(row[0]) for row in conn.execute(user_ids_query, {"email": duplicate_email})]
        
        # Skip the first ID (keep as is) and update the rest with a suffix
        for i, user_id in enumerate(user_ids[1:], 1):
            new_email = f"{duplicate_email.split('@')[0]}+{i}@{duplicate_email.split('@')[1]}"
            
            # Update the email
            update_query = text('''
                UPDATE "user" 
                SET email = :new_email 
                WHERE id = :user_id
            ''')
            
            conn.execute(update_query, {"new_email": new_email, "user_id": user_id})
    
    # Now drop the existing non-unique index
    op.drop_index('ix_user_email', table_name='user')
    
    # And create the unique index
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=True)


def downgrade():
    # Drop the unique index
    op.drop_index('ix_user_email', table_name='user')
    
    # Re-create as non-unique index
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=False)
