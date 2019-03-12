import datetime
from uuid import uuid4

from sqlalchemy import (
    DECIMAL, Column, DateTime, ForeignKey, Integer, String, Boolean, Float, BigInteger
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from enum import Enum, IntEnum
from .exceptions import OrderingException

__schema__ = 'Orders'


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


class Address(DeclarativeBase):
    __tablename__ = 'addresses'
    # __table_args__ = {'schema': __schema__}

    id = Column(BigInteger, primary_key=True)
    street1 = Column(String, nullable=False)
    street2 = Column(String, nullable=True)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    country = Column(String, nullable=False, default='US')
    zip_code = Column(String, nullable=False)


class OrderStatus(IntEnum):
    Submitted = 1
    AwaitingValidation = 2,
    StockConfirmed = 3,
    Paid = 4,
    Shipped = 5,
    Cancelled = 6


class Order(DeclarativeBase):
    __tablename__ = 'orders'
    # __table_args__ = {'schema': __schema__}

    id = Column(BigInteger, primary_key=True)
    customer_id = Column(String, nullable=False)
    address_id = Column(
        BigInteger,
        ForeignKey('addresses.id', name='fk_order_address'),
        nullable=False
    )
    address = relationship(Address)
    card_number = Column(String)
    card_security_number = Column(String)
    cardholder_name = Column(String)
    card_expiration = Column(String)
    payment_method_id = Column(String)
    order_status_id = Column(Integer)
    order_date = Column(DateTime)
    is_draft = Column(Boolean, default=False)
    description = Column(String, nullable=True)

    order_items = []

    def __init__(self):
        self.id = str(uuid4().__hash__())
        self.order_status_id = OrderStatus.Submitted.value

    def add_order_item(self, order_item):
        self.order_items.append(order_item)

    def set_awaiting_validation_status(self):
        if self.order_status_id == OrderStatus.Submitted.value:
            self.order_status_id = OrderStatus.AwaitingValidation.value
            self.updated_at = datetime.datetime.utcnow()

    def set_cancelled_status(self):
        if self.order_status_id == OrderStatus.Paid.value or self.order_status_id == OrderStatus.Shipped.value:
            raise NotImplementedError()

        self.order_status_id = OrderStatus.Cancelled.value
        self.description = 'The order was cancelled'
        super().updated_at = datetime.datetime.utcnow()

    def set_cancelled_status_when_stock_is_rejected(self, order_stock_rejected_items: []):
        if self.order_status_id == OrderStatus.AwaitingValidation.value:
            self.order_status_id = OrderStatus.Cancelled.value

            ls = []

            for item in self.order_items:
                if order_stock_rejected_items.__contains__(item.product_id):
                    ls.append(item.product_name)

            description = ",".join(ls)
            self.description = 'The product items do not have stock: ({})'.format(description)

    def set_stock_confirmed_status(self):
        if self.order_status_id == OrderStatus.AwaitingValidation.value:
            self.order_status_id = OrderStatus.StockConfirmed.value
            self.updated_at = datetime.datetime.utcnow()

    def set_paid_status(self):
        if self.order_status_id == OrderStatus.StockConfirmed.value:
            self.order_status_id = OrderStatus.Paid.value
            self.updated_at = datetime.datetime.utcnow()

    def set_shipped_status(self):
        if self.order_status_id != OrderStatus.Paid.value:
            self.status_change_error(OrderStatus.Shipped.name)

        self.order_status_id = OrderStatus.Shipped.value
        self.updated_at = datetime.datetime.utcnow()

    def get_total(self):
        total = sum([(item.units * item.price for item in self.order_items)])
        return total

    def status_change_error(self, order_status_to_change):
        raise OrderingException(
            f'It is not possible to change the order status from {self.order_status_id} to {order_status_to_change}')


class OrderDetail(DeclarativeBase):
    __tablename__ = 'order_details'
    # __table_args__ = {'schema': __schema__}

    id = Column(BigInteger, primary_key=True)
    order_id = Column(BigInteger, ForeignKey('orders.id', name='fk_order_details_order'))
    order = relationship(Order, backref='order_items')
    product_id = Column(Integer)
    product_name = Column(String)
    unit_price = Column(Float)
    discount = Column(Float)
    units = Column(Integer)

    def __init__(self):
        self.id = str(uuid4())

    def add_units(self, units):
        if units < 0:
            raise OrderingException('Invalid units')

        self.units += units

    def set_new_discount(self, discount):
        if discount < 0:
            raise OrderingException('Invalid discount')

        self.discount = discount
