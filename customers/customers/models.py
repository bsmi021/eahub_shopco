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

class PaymentMethod(DeclarativeBase):
    __tablename__ = 'payment_methods'
    id = Column(Integer, primary_key=True, autoincrement=True)
    alias = Column(String, nullable=False)
    card_number = Column(String)
    security_number = Column(String)
    cardholder_name = Column(String)
    expiration = Column(String)
    card_type_id = Column(Integer)
    customer_id = Column(
        Integer,
        ForeignKey('customers.id', name='fk_payment_method_customer')
    )
    customer = relationship('Customer', backref='payment_methods')

    def is_equal_to(self, card_type_id, card_number, expiration):
        return (self.card_type_id == card_type_id and
                self.card_number == card_number and
                self.expiration == expiration)

class Customer(DeclarativeBase):
    __tablename__ = 'customers'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    street_1 = Column(String, nullable=False)
    street_2 = Column(String, nullable=True)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    country = Column(String, nullable=False, default='US')
    zip_code = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    user_id = Column(Integer, nullable=True)

    def verify_or_add_payment(self, card_type_id, alias, card_number, security_number, card_holder_name,
                              expiration, order_id) -> PaymentMethod:
        """ use this method to add a payment method for a buyer, this will determine
        if the buyer has not already been used this payment method it'll be stored """

        existing_payment = None

        for p in self.payment_methods:
            if p.is_equal_to(card_type_id, card_number, expiration):
                existing_payment = p
                break

        if existing_payment is not None:
            # TODO enter logic for BuyerAndPaymentMethodVerified
            return existing_payment

        payment = PaymentMethod(card_type_id, alias, card_number, security_number, card_holder_name, expiration)

        self.payment_methods.append(payment)
        # TODO enter logic for BuyerAndPaymentMethodVerified
        return payment



connect(os.getenv('MONGO_DATABASE', 'customers'),
        host=os.environ.get('MONGO_HOST', '127.0.0.1'),
        port=int(os.environ.get('MONGO_PORT', 27017)))


class CardType:
    AMEX = 1
    VISA = 2
    MASTERCARD = 3
    DINER = 4


class QueryPaymentMethodModel(EmbeddedDocument):
    id = IntField(primary_key=True)
    alias = StringField()
    card_number = StringField()
    security_number = StringField()
    cardholder_name = StringField()
    expiration = StringField()
    card_type_id = IntField()
    created_at = StringField()
    updated_at = StringField()

    def create (self, dictionary):
        for key in dictionary:
            setattr(self, key, dictionary[key])


class QueryCustomersModel(Document):
    id = IntField(primary_key=True)
    payment_methods = ListField(EmbeddedDocumentField(QueryPaymentMethodModel))
    name = StringField()
    last_name = StringField()
    street_1 = StringField()
    street_2 = StringField()
    city = StringField()
    state = StringField()
    country = StringField(default='US')
    zip_code = StringField()
    email = StringField(unique=True)
    phone = StringField()
    created_at = StringField()
    updated_at = StringField()

    #def __init__(self):
    #    super(Customer, self).__init__()
    #    self.id = uuid4().__str__()





