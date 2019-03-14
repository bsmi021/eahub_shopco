import datetime
import os
from mongoengine import *
from sqlalchemy.dialects import postgresql


from sqlalchemy import (
    DECIMAL, Column, DateTime, ForeignKey, Integer, String, Boolean
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


class Base(object):
    created_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        nullable=False
    )
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        nullable=False
    )


DeclarativeBase = declarative_base(cls=Base)


class ProductBrand(DeclarativeBase):
    __tablename__ = 'product_brands'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)


class Product(DeclarativeBase):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(String)
    price = Column(DECIMAL(10,2))
    product_brand_id = Column(
        Integer,
        ForeignKey("product_brands.id", name='fk_product_product_brand'),
        nullable=False
    )
    product_brand = relationship(ProductBrand, backref='products')
    available_stock = Column(Integer, nullable=False, default=1)
    restock_threshold = Column(Integer, nullable=False, default=0)
    max_stock_threshold = Column(Integer, nullable=False, default=1000)
    on_reorder = Column(Boolean, nullable=False, default=False)


    def remove_stock(self, quantity_desired):
        """ decreements the quantity of an item from inventory"""

        if self.available_stock == 0:
            return 0

        if quantity_desired <= 0:
            return 0

        removed = min(quantity_desired, self.available_stock)

        self.available_stock -= removed

        if self.available_stock <= self.restock_threshold:
            self.on = True

        return removed

    def add_stock(self, quantity):
        """ increments the quantity of a particular item in inventory"""

        original = self.available_stock

        # the quantity that the client is tryintg to add to stock is greater than what the warehouse can accomodate
        if (self.available_stock + quantity) > self.max_stock_threshold:
            # only add the amount of items that will cover max_stock_threshold, rest will be disgarded for this
            self.available_stock += (self.max_stock_threshold - self.available_stock)
        else:
            self.available_stock += quantity

        self.on_reorder = False

        return self.available_stock - original

connect(os.getenv('MONGO_DATABASE', 'products'),
        host=os.environ.get('MONGO_HOST', '127.0.0.1'),
        port=int(os.environ.get('MONGO_PORT', 27017)))


class QueryBrandModel(Document):
    id = IntField(primary_key=True)
    name = StringField()


class QueryProductsModel(Document):
    id = IntField(primary_key=True)
    name = StringField()
    description = StringField()
    price = FloatField()
    available_stock = IntField()
    restock_threshold = IntField()
    on_reorder = BooleanField()
    max_stock_threshold = IntField()