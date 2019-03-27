import datetime
import os
from mongoengine import *
from sqlalchemy.dialects import postgresql

from sqlalchemy import (
    DECIMAL, Column, DateTime, ForeignKey, BigInteger, String, Boolean
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


class Account(DeclarativeBase):
    __tablename__ = 'accounts'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_name = Column(String(64), index=True, nullable=False, unique=True)
    password_hash = Column(String(128), nullable=False)
    email = Column(String(120), index=True, nullable=False, unique=True)


class Customer(DeclarativeBase):
    __tablename__ = 'customers'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    full_name = Column(String, nullable=False)
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
    account_id = Column(BigInteger,
                        ForeignKey('accounts.id', name='fk_customers_accounts'), nullable=True)
    account = relationship('Account', backref='customers')


connect(os.getenv('MONGO_DATABASE', 'customers'),
        host=os.environ.get('MONGO_HOST', '127.0.0.1'),
        port=int(os.environ.get('MONGO_PORT', 27017)))


class QueryCustomersModel(Document):
    id = IntField(primary_key=True)
    full_name = StringField()
    name = StringField()
    last_name = StringField()
    street_1 = StringField()
    street_2 = StringField()
    city = StringField()
    state = StringField()
    country = StringField(default='US')
    zip_code = StringField()
    email = StringField()
    phone = StringField()
    created_at = StringField()
    updated_at = StringField()
    account_id = IntField()
