"""rename_otp_table_to_verification

Revision ID: 9b1529955588
Revises: d0894736bf88
Create Date: 2025-04-11 12:40:01.715315

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from sqlalchemy import text
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '9b1529955588'
down_revision = 'd0894736bf88'
branch_labels = None
depends_on = None


def index_exists(conn, index_name):
    """Check if an index exists in PostgreSQL"""
    query = text("""
        SELECT 1
        FROM pg_indexes
        WHERE indexname = :index_name
    """)
    result = conn.execute(query, {"index_name": index_name})
    return result.scalar() is not None


def constraint_exists(conn, constraint_name, table_name):
    """Check if a constraint exists in PostgreSQL"""
    query = text("""
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_name = :constraint_name
        AND table_name = :table_name
    """)
    result = conn.execute(query, {"constraint_name": constraint_name, "table_name": table_name})
    return result.scalar() is not None


def table_exists(conn, table_name):
    """Check if a table exists in PostgreSQL"""
    query = text("""
        SELECT 1
        FROM information_schema.tables
        WHERE table_name = :table_name
    """)
    result = conn.execute(query, {"table_name": table_name})
    return result.scalar() is not None


def upgrade():
    # Create connection to execute raw SQL
    conn = op.get_bind()
    
    # Check if otp table exists
    if not table_exists(conn, 'otp'):
        # If otp table doesn't exist, just create the verification table
        op.create_table('verification',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('application_id', sa.UUID(), nullable=False),
            sa.Column('email', sa.String(length=255), nullable=False),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('code', sa.String(length=6), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.Column('is_verified', sa.Boolean(), server_default='False', nullable=False),
            sa.ForeignKeyConstraint(['application_id'], ['application.id'], name='verification_application_id_fkey'),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes on the new verification table
        op.create_index(op.f('ix_verification_application_id'), 'verification', ['application_id'], unique=False)
        op.create_index(op.f('ix_verification_email'), 'verification', ['email'], unique=False)
        op.create_index(op.f('ix_verification_user_id'), 'verification', ['user_id'], unique=False)
        return
    
    # Create the new verification table
    op.create_table('verification',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('application_id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('code', sa.String(length=6), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), server_default='False', nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['application.id'], name='verification_application_id_fkey'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes on the new verification table
    op.create_index(op.f('ix_verification_application_id'), 'verification', ['application_id'], unique=False)
    op.create_index(op.f('ix_verification_email'), 'verification', ['email'], unique=False)
    op.create_index(op.f('ix_verification_user_id'), 'verification', ['user_id'], unique=False)
    
    # Copy data from otp to verification
    try:
        op.execute("""
            INSERT INTO verification (id, application_id, email, user_id, code, created_at, expires_at, is_verified)
            SELECT id, application_id, email, user_id, code, created_at, expires_at, is_verified FROM otp
        """)
    except Exception as e:
        print(f"Warning: Could not copy data from otp to verification: {e}")
    
    # Drop foreign key constraint from otp table if it exists
    if constraint_exists(conn, 'otp_application_id_fkey', 'otp'):
        op.drop_constraint('otp_application_id_fkey', 'otp', type_='foreignkey')
    
    # Drop indexes from otp table if they exist
    if index_exists(conn, 'ix_otp_user_id'):
        op.drop_index(op.f('ix_otp_user_id'), table_name='otp')
    
    if index_exists(conn, 'ix_otp_email'):
        op.drop_index(op.f('ix_otp_email'), table_name='otp')
    
    if index_exists(conn, 'ix_otp_application_id'):
        op.drop_index(op.f('ix_otp_application_id'), table_name='otp')
    
    # Drop the old otp table
    op.drop_table('otp')


def downgrade():
    # Create connection to execute raw SQL
    conn = op.get_bind()
    
    # Check if verification table exists
    if not table_exists(conn, 'verification'):
        return
    
    # Create the otp table
    op.create_table('otp',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('application_id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('code', sa.String(length=6), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), server_default='False', nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['application.id'], name='otp_application_id_fkey'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes on the otp table
    op.create_index(op.f('ix_otp_application_id'), 'otp', ['application_id'], unique=False)
    op.create_index(op.f('ix_otp_email'), 'otp', ['email'], unique=False)
    op.create_index(op.f('ix_otp_user_id'), 'otp', ['user_id'], unique=False)
    
    # Copy data from verification to otp
    try:
        op.execute("""
            INSERT INTO otp (id, application_id, email, user_id, code, created_at, expires_at, is_verified)
            SELECT id, application_id, email, user_id, code, created_at, expires_at, is_verified FROM verification
        """)
    except Exception as e:
        print(f"Warning: Could not copy data from verification to otp: {e}")
    
    # Drop foreign key constraint from verification table if it exists
    if constraint_exists(conn, 'verification_application_id_fkey', 'verification'):
        op.drop_constraint('verification_application_id_fkey', 'verification', type_='foreignkey')
    
    # Drop indexes from verification table if they exist
    if index_exists(conn, 'ix_verification_user_id'):
        op.drop_index(op.f('ix_verification_user_id'), table_name='verification')
    
    if index_exists(conn, 'ix_verification_email'):
        op.drop_index(op.f('ix_verification_email'), table_name='verification')
    
    if index_exists(conn, 'ix_verification_application_id'):
        op.drop_index(op.f('ix_verification_application_id'), table_name='verification')
    
    # Drop the verification table
    op.drop_table('verification')
