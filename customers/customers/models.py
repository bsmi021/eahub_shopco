from mongoengine import *
from uuid import uuid4
from enum import IntEnum
from datetime import datetime
import os

connect(os.getenv('MONGO_DATABASE', 'customers'),
        host=os.environ.get('MONGO_HOST', '127.0.0.1'),
        port=int(os.environ.get('MONGO_PORT', 27017)))


class CardType(IntEnum):
    AMEX = 1
    VISA = 2
    MASTERCARD = 3
    DINER = 4


class PaymentMethod(Document):
    id = StringField(primary_key=True, default=uuid4().__str__())
    alias = StringField()
    card_number = StringField()
    security_number = StringField()
    cardholder_name = StringField()
    expiration = StringField()
    card_type_id = IntField()
    customer_id = StringField()
    customer = ReferenceField('Customer')

    def create (self, dictionary):
        for key in dictionary:
            setattr(self, key, dictionary[key])

    def is_equal_to(self, card_type_id, card_number, expiration):
        return (self.card_type_id == card_type_id and
                self.card_number == card_number and
                self.expiration == expiration)



class Customer(Document):
    id = StringField(primary_key=True, default=uuid4().__str__())
    payment_methods = ListField(ReferenceField(PaymentMethod))
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
    created_at = DateTimeField(default=datetime.utcnow())
    updated_at = DateTimeField(default=datetime.utcnow())

    #def __init__(self):
    #    super(Customer, self).__init__()
    #    self.id = uuid4().__str__()





