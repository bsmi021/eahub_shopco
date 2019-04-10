import datetime
import os
from mongoengine import *
from sqlalchemy.dialects import postgresql
import random

from sqlalchemy import (
   Index, DECIMAL, Column, DateTime, ForeignKey, BigInteger, String, Boolean, Integer
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

SiteTypes = { 1: 'Distribution Center',
              2: 'Store',
              3: 'Forward Shipping'}


class Site(DeclarativeBase):
    __tablename__ = 'sites'
    id = Column(BigInteger, autoincrement=True, primary_key=True)
    name = Column(String(50), nullable=False)
    zip_code = Column(String(12), nullable=False)
    type_id = Column(Integer, nullable=False)  # 1 DC 2 Store


class InventoryItem(DeclarativeBase):
    __tablename__ = 'inventory_items'
    id = Column(BigInteger, primary_key=True)
    version = Column(BigInteger, primary_key=True, default=1)
    product_id = Column(BigInteger, primary_key=True, nullable=False)
    site_id = Column(BigInteger,  ForeignKey('sites.id', name='fk_inventory_items_site'), primary_key=True, nullable=False)
    on_reorder = Column(Boolean, default=False)
    restock_threshold = Column(Integer, nullable=False, default=0)
    max_stock_threshold = Column(Integer, nullable=False, default=0)
    available_stock = Column(Integer, nullable=False, default=0)
    committed_stock = Column(Integer, nullable=False, default=0)

    __table_args__ = Index('index', 'id', 'version'),

    def __init__(self, product_id, site_id):
        max_stock_threshold = random.randint(105, 1050)
        restock_threshold = random.randint(10, 50)
        available_stock = random.randint(restock_threshold + 5, max_stock_threshold)

        self.available_stock = available_stock
        self.max_stock_threshold = max_stock_threshold
        self.restock_threshold = restock_threshold

        self.product_id = product_id
        self.site_id = site_id


    def remove_stock(self, quantity_desired):
        """ decreements the quantity of an item from inventory"""

        if self.available_stock == 0:
            return 0

        if quantity_desired <= 0:
            return 0

        removed = min(quantity_desired, self.available_stock)

        self.available_stock -= removed

        if self.available_stock <= self.restock_threshold:
            self.on_reorder = True

        self.updated_at = datetime.datetime.utcnow()

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


connect(os.getenv('MONGO_DATABASE', 'warehouse'),
        host=os.environ.get('MONGO_HOST', '127.0.0.1'),
        port=int(os.environ.get('MONGO_PORT', 27017)))


class SiteQueryModel(Document):
    id = IntField(primary_key=True)
    name = StringField()
    zip_code = StringField()
    type_id = IntField()
    type = StringField()
    created_at = StringField()
    updated_at = StringField()


class InventoryItemQueryModel(Document):
    id = IntField(primary_key=True)
    version = IntField()
    product_id = IntField()
    site_id = IntField()
    on_reorder = BooleanField()
    restock_threshold = IntField()
    max_stock_threshold = IntField()
    available_stock = IntField()
    created_at = StringField()
    updated_at = StringField()
    committed_stock = IntField()
