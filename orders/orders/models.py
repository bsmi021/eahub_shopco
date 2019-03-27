import datetime
import os
from enum import IntEnum

from mongoengine import *
from py_linq import Enumerable
from sqlalchemy import (
    Column, DateTime, ForeignKey, Integer, String, Boolean, Float, BigInteger
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from .exceptions import OrderingException


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


class CommandAddressModel(DeclarativeBase):
    __tablename__ = 'addresses'
    # __table_args__ = {'schema': __schema__}

    id = Column(BigInteger, primary_key=True)
    street1 = Column(String, nullable=False)
    street2 = Column(String, nullable=True)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    country = Column(String, nullable=False, default='US')
    zip_code = Column(String, nullable=False)

    def __init__(self, street_1, street_2, city, state, country, zip_code):
        self.street1 = street_1
        self.street2 = street_2
        self.city = city
        self.state = state
        self.country = country
        self.zip_code = zip_code


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

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    customer_id = Column(String, nullable=False)
    address_id = Column(
        BigInteger,
        ForeignKey('addresses.id', name='fk_order_address'),
        nullable=False
    )
    address = relationship(CommandAddressModel)
    buyer_id = Column(Integer,
                      ForeignKey('buyers.id', name='fk_order_buyers'), nullable=True)
    buyer = relationship('Buyer', backref='order')

    payment_method_id = Column(Integer,
                               ForeignKey('payment_methods.id', name='fk_order_payment_methods'))
    payment_method = relationship('PaymentMethod')

    order_status_id = Column(Integer)
    order_date = Column(DateTime, default=datetime.datetime.utcnow())
    is_draft = Column(Boolean, default=False)
    description = Column(String, nullable=True)

    order_items = []

    def __init__(self, customer_id, address):
        self.order_status_id = OrderStatus.Submitted.value
        self.customer_id = customer_id
        self.address = address
        self.order_date = datetime.datetime.utcnow()

    def get_total(self):
        return Enumerable(self.order_items).sum(lambda x: x.units * x.unit_price)

    def add_order_item(self, product_id, product_name, unit_price, units=1, discount=0):
        """
        Checks to see if the order line item exists, updates the discount and units, otherwise
        it will create the item and add it to the order
        :param product_id:
        :param product_name:
        :param unit_price:
        :param units:
        :param discount:
        :return:
        """
        existing_order_line = Enumerable(self.order_items) \
            .where(lambda x: x.product_id == product_id).first_or_default()

        if existing_order_line is not None:
            if discount > existing_order_line.discount:
                existing_order_line.set_new_discount(discount)

            existing_order_line.add_units(units)
        else:
            order_item = OrderItem(product_id, product_name, unit_price, units, discount)
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
        self.updated_at = datetime.datetime.utcnow()

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
            self.description = 'The payment for this order has been performed (simulated)'

    def set_shipped_status(self):
        if self.order_status_id != OrderStatus.Paid.value:
            self.status_change_error(OrderStatus.Shipped.name)

        self.order_status_id = OrderStatus.Shipped.value
        self.updated_at = datetime.datetime.utcnow()
        self.description = 'The order was shipped.'

    def get_total(self):
        total = sum([(item.units * item.price for item in self.order_items)])
        return total

    def status_change_error(self, order_status_to_change):
        raise OrderingException(
            f'It is not possible to change the order status from {self.order_status_id} to {order_status_to_change}')


class OrderItem(DeclarativeBase):
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

    def __init__(self, product_id, product_name, unit_price, units, discount=0):
        self.product_id = product_id
        self.product_name = product_name
        self.unit_price = unit_price
        self.discount = discount
        self.units = units

    def add_units(self, units):
        if units < 0:
            raise OrderingException('Invalid units')

        self.units += units

    def set_new_discount(self, discount):
        if discount < 0:
            raise OrderingException('Invalid discount')

        self.discount = discount


class Buyer(DeclarativeBase):
    __tablename__ = 'buyers'
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    name = Column(String, nullable=False)
    payment_methods = []

    def __init__(self, user_id, name):
        self.user_id = user_id
        self.name = name

    def verify_or_add_payment_method(self, alias, card_number, security_number, card_type_id,
                                     cardholder_name, expiration):
        existing_payment = Enumerable(self.payment_methods) \
            .where(lambda x: x.is_equal_to(card_type_id, card_number, expiration)) \
            .first_or_default()

        if existing_payment is not None:
            return existing_payment
        else:
            payment = PaymentMethod()
            payment.buyer = self
            payment.card_number = card_number
            payment.expiration = expiration
            payment.card_type_id = card_type_id
            payment.alias = alias
            payment.cardholder_name = cardholder_name
            payment.security_number = security_number

            self.payment_methods.append(payment)

            return payment


class PaymentMethod(DeclarativeBase):
    __tablename__ = 'payment_methods'

    id = Column(BigInteger, primary_key=True)
    buyer_id = Column(BigInteger,
                      ForeignKey('buyers.id', name='fk_payment_methods_buyers'))
    buyer = relationship(Buyer, backref='payment_methods')
    card_type_id = Column(Integer)
    cardholder_name = Column(String)
    alias = Column(String)
    card_number = Column(String)
    expiration = Column(String)
    security_number = Column(String)

    def is_equal_to(self, card_type_id, card_number, expiration):
        return (
                self.card_type_id == card_type_id and
                self.card_number == card_number and
                self.expiration == expiration
        )


connect(os.getenv('MONGO_DATABASE', 'orders'),
        host=os.getenv('MONGO_HOST', '127.0.0.1'),
        port=int(os.getenv('MONGO_PORT', 27017)))


class QueryAddressModel(EmbeddedDocument):
    id = IntField(primary_key=True),
    street_1 = StringField()
    street_2 = StringField()
    city = StringField()
    state = StringField()
    zip_code = StringField()
    country = StringField()


class QueryOrderItemModel(EmbeddedDocument):
    id = IntField(primary_key=True)
    product_id = IntField()
    product_name = StringField()
    unit_price = FloatField()
    discount = FloatField()
    units = IntField()


class QueryBuyerModel(EmbeddedDocument):
    id = IntField(primary_key=True)
    name = StringField()


class QueryPaymentMethod(EmbeddedDocument):
    id = IntField(primary_key=True)
    alias = StringField()
    cardholder_name = StringField()
    expiration = StringField()
    card_number = StringField()


class QueryOrderModel(Document):
    id = IntField(primary_key=True)
    customer_id = IntField()
    order_status_id = IntField()
    order_date = StringField()
    description = StringField()
    created_at = StringField()
    updated_at = StringField()
    buyer_id = IntField()
    order_items = EmbeddedDocumentListField(QueryOrderItemModel)
    buyer = EmbeddedDocumentField(QueryBuyerModel)
    address = EmbeddedDocumentField(QueryAddressModel)
    payment_method = EmbeddedDocumentField(QueryPaymentMethod)
