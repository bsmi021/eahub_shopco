"""baseline

Revision ID: 9b0d71a40ad3
Revises: 
Create Date: 2019-02-28 07:13:08.233945

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9b0d71a40ad3'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "product_brands",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id")
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("price", sa.DECIMAL(10,2), nullable=False),
        sa.Column("available_stock", sa.Integer(), nullable=False),
        sa.Column("restock_threshold", sa.Integer(), nullable=False),
        sa.Column("max_stock_threshold", sa.Integer(), nullable=False),
        sa.Column("on_reorder", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("product_brand_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["product_brand_id"], ["product_brands.id"],
            name="fk_products_product_brands"
        ),
    )


def downgrade():
    op.drop_table("products")
    op.drop_table("product_brands")
