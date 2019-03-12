"""empty message

Revision ID: f259e993052e
Revises: 
Create Date: 2019-03-06 11:11:43.403781

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f259e993052e'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('addresses',
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('street1', sa.String(), nullable=False),
    sa.Column('street2', sa.String(), nullable=True),
    sa.Column('city', sa.String(), nullable=False),
    sa.Column('state', sa.String(), nullable=False),
    sa.Column('country', sa.String(), nullable=False),
    sa.Column('zip_code', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('orders',
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('customer_id', sa.String(), nullable=False),
    sa.Column('address_id', sa.BigInteger(), nullable=False),
    sa.Column('card_number', sa.String(), nullable=True),
    sa.Column('card_security_number', sa.String(), nullable=True),
    sa.Column('cardholder_name', sa.String(), nullable=True),
    sa.Column('card_expiration', sa.String(), nullable=True),
    sa.Column('payment_method_id', sa.String(), nullable=True),
    sa.Column('order_status_id', sa.Integer(), nullable=True),
    sa.Column('order_date', sa.DateTime(), nullable=True),
    sa.Column('is_draft', sa.Boolean(), nullable=True),
    sa.Column('description', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['address_id'], ['addresses.id'], name='fk_order_address'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('order_details',
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('order_id', sa.BigInteger(), nullable=True),
    sa.Column('product_id', sa.Integer(), nullable=True),
    sa.Column('product_name', sa.String(), nullable=True),
    sa.Column('unit_price', sa.Float(), nullable=True),
    sa.Column('discount', sa.Float(), nullable=True),
    sa.Column('units', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name='fk_order_details_order'),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('order_details')
    op.drop_table('orders')
    op.drop_table('addresses')
    # ### end Alembic commands ###