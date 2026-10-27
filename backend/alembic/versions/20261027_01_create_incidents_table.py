"""create incidents table

Revision ID: 20261027_01
Revises: 
Create Date: 2026-10-27 19:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20261027_01'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create incidents table if not exists
    op.create_table(
        'incidents',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('address', sa.String(length=255), nullable=True),
        sa.Column('location_name', sa.String(length=255), nullable=True),
        sa.Column('incident_category', sa.String(length=64), nullable=False),
        sa.Column('severity', sa.String(length=32), nullable=False, server_default='MODERATE'),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('reporter_name', sa.String(length=128), nullable=True),
        sa.Column('reporter_contact', sa.String(length=128), nullable=True),
        sa.Column('has_image', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('image_data', sa.Text(), nullable=True),
        sa.Column('verification_status', sa.String(length=32), nullable=False, server_default='PENDING_REVIEW'),
        sa.Column('data_status', sa.String(length=32), nullable=False, server_default='PUBLIC_UNVERIFIED_REPORT'),
        sa.Column('duplicate_of_id', sa.String(length=32), nullable=True),
        sa.Column('report_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verification_note', sa.Text(), nullable=True),
        sa.Column('client_ip', sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_incidents_id', 'incidents', ['id'], unique=False)
    op.create_index('ix_incidents_spatial', 'incidents', ['latitude', 'longitude'], unique=False)
    op.create_index('ix_incidents_status_cat', 'incidents', ['verification_status', 'incident_category'], unique=False)
    op.create_index('ix_incidents_severity', 'incidents', ['severity'], unique=False)
    op.create_index('ix_incidents_duplicate_of', 'incidents', ['duplicate_of_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_incidents_duplicate_of', table_name='incidents')
    op.drop_index('ix_incidents_severity', table_name='incidents')
    op.drop_index('ix_incidents_status_cat', table_name='incidents')
    op.drop_index('ix_incidents_spatial', table_name='incidents')
    op.drop_index('ix_incidents_id', table_name='incidents')
    op.drop_table('incidents')
