import logging
import os
import datetime
import json

from mongoengine import connect
from nameko.events import event_handler, EventDispatcher
from nameko.rpc import rpc
from nameko_sqlalchemy import DatabaseSession

from .exceptions import *
from .models import *
from .schemas import *

logger = logging.getLogger(__name__)

REPLICATE_DB_EVENT = 'replicate_db_event'
COMMAND_SERVICE = 'command_customers'
QUERY_SERVICE = 'query_customers'
ORDERS_SERVICE = os.environ.get('ORDERS_COMMAND', 'command_orders')


class Command:
    name = COMMAND_SERVICE
    dispatch = EventDispatcher()
    db = DatabaseSession(DeclarativeBase)

    def fire_replicate_db_event(self, data):
        self.dispatch(REPLICATE_DB_EVENT, data)

    @rpc
    def add(self, data):
        customer = Customer()
        customer.name = data.get('name')
        customer.phone = data.get('phone', '')
        customer.email = data.get('email')
        customer.last_name = data.get('last_name')
        customer.state = data.get('state')
        customer.street_2 = data.get('street_2')
        customer.street_1 = data.get('street_1')
        customer.city = data.get('city')
        customer.country = data.get('country')
        customer.zip_code = data.get('zip_code')

        self.db.add(customer)
        self.db.commit()

        data['id'] = customer.id
        data['created_at'] = customer.created_at
        data['updated_at'] = customer.updated_at

        data = CustomerSchema().dumps(customer).data

        self.fire_replicate_db_event(data)

        return data

    @rpc
    def update(self, id, data):
        customer = self.db.query(Customer).get(data['id'])

        if customer is None:
            raise NotFound('Customer was not found.')

        customer.name = data.get('name', customer.name)
        customer.phone = data.get('phone', customer.phone)
        customer.email = data.get('email', customer.email)
        customer.last_name = data.get('last_name', customer.last_name)
        customer.state = data.get('state', customer.state)
        customer.street_2 = data.get('street_2', customer.street_2)
        customer.street_1 = data.get('street_1', customer.street_1)
        customer.city = data.get('city', customer.city)
        customer.country = data.get('country', customer.country)
        customer.zip_code = data.get('zip_code', customer.zip_code)
        customer.updated_at = datetime.datetime.utcnow()

        self.db.add(customer)
        self.db.commit()

        data['created_at'] = customer.created_at
        data['updated_at'] = customer.updated_at

        data = CustomerSchema().dumps(customer).data

        self.fire_replicate_db_event(data)

        return data

    @rpc
    def add_payment_method(self, id, data):
        """
        Add a new payment method to the customer's profile
        :param id:
        :param data:
        :return:
        """
        customer = self.db.query(Customer).get(id)

        if customer is None:
            raise NotFound('Customer not found for id:{}'.format(id))

        exists = any(payment.is_equal_to(data['card_type_id'], data['card_number'], data['expiration'])
                     for payment in customer.payment_methods)

        if exists:
            return None

        payment_method = PaymentMethod()
        payment_method.alias = data.get('alias', 'card')
        payment_method.customer = customer
        payment_method.card_number = data['card_number']
        payment_method.security_number = data['security_number']
        payment_method.expiration = data['expiration']
        payment_method.card_type_id = data['card_type_id']
        payment_method.cardholder_name = data['cardholder_name']

        customer.payment_methods.append(payment_method)
        customer.updated_at = datetime.datetime.utcnow()

        self.db.add(payment_method)
        self.db.add(customer)
        self.db.commit()

        data['id'] = payment_method.id
        data['customer_id'] = payment_method.customer_id

        self.fire_replicate_db_event(CustomerSchema().dumps(customer).data)

        return data

    @event_handler(ORDERS_SERVICE, 'verify_customer_payment')
    def verify_customer_payment(self, data):
        """ this handler will add a payment method for a customer if the
        provided values do not match any existing payment method assigned to the
        customer"""

        customer = self.db.query(Customer).get(data.get('customer_id'))

        if customer is None:
            raise NotFound('Customer not found for id:{}'.format(id))
        existing_payment = None
        for payment in customer.payment_methods:
            if payment.is_equal_to(data['card_type_id'],
                                   data['card_number'],
                                   data['expiration']):
                existing_payment = payment
                data['id'] = existing_payment.id
                break

        if existing_payment is not None:
            self.dispatch('payment_verified', data)

        payment = self.add_payment_method(data['customer_id'], data)
        data['id'] = payment.id

        self.dispatch('payment_verified', data)

class Query:
    name = QUERY_SERVICE

    @event_handler(COMMAND_SERVICE, REPLICATE_DB_EVENT)
    def normalize_db(self, data):
        """ with the incoming payload:
        check to see if the record already exists in the query database
        if so, updated it with the new replicated values, otherwise add
        the record to the query database"""

        data = json.loads(data)

        try:
            customer = QueryCustomersModel.objects.get(
                id=data['id']
            )

            payment_methods = []

            for method in data['payment_methods']:
                payment_method = QueryPaymentMethodModel(
                    id=method.get('id'),
                    alias=method.get('alias'),
                    card_number=method.get('card_number'),
                    card_type_id=method.get('card_type_id'),
                    security_number=method.get('security_number'),
                    expiration=method.get('expiration'),
                    cardholder_name=method.get('cardholder_name'),
                    created_at=method.get('created_at'),
                    updated_at=method.get('updated_at')
                )
                payment_methods.append(payment_method)

            customer.update(
                name=data.get('name', customer.name),
                phone=data.get('phone', customer.phone),
                email=data.get('email', customer.email),
                last_name=data.get('last_name', customer.last_name),
                state=data.get('state', customer.state),
                street_2=data.get('street_2', customer.street_2),
                street_1=data.get('street_1', customer.street_1),
                city=data.get('city', customer.city),
                country=data.get('country', customer.country),
                zip_code=data.get('zip_code', customer.zip_code),
                created_at=data.get('created_at', customer.created_at),
                updated_at=data.get('updated_at', customer.updated_at),
                payment_methods=payment_methods
            )
            customer.reload()
        except DoesNotExist:
            QueryCustomersModel(
                id=data['id'],
                name=data['name'],
                phone=data['phone'],
                email=data['email'],
                last_name=data['last_name'],
                state=data['state'],
                street_2=data.get('street_2', ''),
                street_1=data['street_1'],
                city=data['city'],
                country=data['country'],
                zip_code=data['zip_code'],
                created_at=data['created_at'],
                updated_at=data['updated_at']
            ).save()
        except Exception as e:
            logger.error('{}: There was a problem replicating {}'.format(datetime.datetime.utcnow(), e))
            return e

    @rpc
    def list(self, num_page=1, limit=0):
        """ returns all of the customers"""
        try:
            if not num_page:
                num_page = 1
            offset = (num_page - 1) * limit
            customers = QueryCustomersModel.objects \
                # .skip(offset).limit(limit)
            return customers.to_json()
        except Exception as e:
            return e

    @rpc
    def get(self, id):
        """ returns a single customer based on the ID"""
        try:
            customer = QueryCustomersModel.objects.get(id=id)
            return customer.to_json()
        except DoesNotExist as e:
            raise NotFound('Customer for ID {} does not exist'.format(id))
        except Exception as e:
            return e






#
# class CustomersService:
#     name = "customers_service"
#
#     connect(os.getenv('MONGO_DATABASE', 'customers'),
#             host=os.getenv('MONGO_HOST', '127.0.0.1'),
#             port=int(os.getenv('MONGO_PORT', 27017)))
#
#     fire_event = EventDispatcher()
#
#     def __init__(self):
#         logger.info('Connecting to {}:{} {} for mongodb'.format(
#             os.getenv('MONGO_HOST', '127.0.0.1'),
#             os.getenv('MONGO_PORT', 27017),
#             os.getenv('MONGO_DATABASE', 'customers')
#         ))
#
#     @rpc
#     def list(self):
#         response = [CustomerSchema().dump(customer).data
#                     for customer in CustomerQueryModel.objects]
#
#         return response
#
#     @rpc
#     def get(self, id):
#         """ Returns a customer based on the provided id"""
#         customer = CustomerQueryModel.objects.get(id=id).select_related()
#         return CustomerSchema().dumps(customer).data
#
#     @rpc
#     def create(self, payload):
#         """
#         Creates a new customer and payment method.
#
#         Expects:
#         {
#             "name":<string>,
#             "last_name":<string>,
#             "street_1":<string>,
#             "street_2":<string>,
#             "city":<string>,
#             "state":<string>,
#             "zip_code":<string>,
#             "email":<string>,
#             "phone":<string>,
#             <! optional !>
#             "cardholder_name":<string>
#             "card_number":<string>
#             "card_type_id":<int>
#             "security_number":<string>
#             "alias":<string>
#         }
#         :param payload:
#         :return:
#         """
#         customer = CustomerQueryModel()
#         customer.name = payload["name"]
#         customer.last_name = payload["last_name"]
#         customer.street_1 = payload["street_1"]
#         customer.street_2 = payload["street_2"]
#         customer.state = payload["state"]
#         customer.city = payload["city"]
#         customer.zip_code = payload["zip_code"]
#         customer.email = payload["email"]
#         customer.phone = payload["phone"]
#
#         customer.save(cascade=True)
#
#         if payload['payment_method'] is not None:
#             pay_method = PaymentMethodQueryModel()
#
#             payment_method = payload['payment_method']
#             pay_method.cardholder_name = payment_method['cardholder_name']
#             pay_method.card_number = payment_method['card_number']
#             pay_method.card_type_id = payment_method['card_type_id']
#             pay_method.security_number = payment_method['security_number']
#
#             customer.payment_methods.append(pay_method)
#             pay_method.customer = customer
#             pay_method.save(cascade=True)
#
#         customer = CustomerQueryModel.objects.get(id=customer.id).select_related(1)
#
#         return CustomerSchema().dumps(customer).data
#
#     @rpc
#     def add_payment_method(self, payload):
#         """ Creates a new payment method for the customer specified in the
#         payload's customer_id key
#
#         expects:
#         {
#             "customer_id":,
#             "cardholder_name":,
#             "expiration":,
#             "card_number":,
#             "security_number":,
#             "card_type_id":,
#             "alias":,
#
#         }
#         """
#         customer = CustomerQueryModel.objects(id=payload['customer_id']).first()
#
#         if customer is None:
#             raise NotFound()
#
#         pay_method = PaymentMethodQueryModel()
#         pay_method.cardholder_name = payload['cardholder_name']
#         pay_method.card_number = payload['card_number']
#         pay_method.card_type_id = payload['card_type_id']
#         pay_method.security_number = payload['security_number']
#         pay_method.alias = payload['alias']
#         pay_method.expiration = payload['expiration']
#
#         pay_method.customer = customer
#         customer.payment_methods.append(pay_method)
#         pay_method.save(cascade=True)
#
#         return PaymentMethodSchema().dumps(pay_method).data
#
#     @rpc
#     def get_payment_method_by_customer_id(self, customer_id):
#         """
#         Returns the payment methods for the customer_id provided
#         :param customer_id:
#         :return:
#         """
#
#         payments = PaymentMethodQueryModel.objects(customer=customer_id)
#
#         results = [PaymentMethodSchema().dump(payment).data
#                    for payment in payments]
#
#         return results
#
#     @event_handler('orders_service', 'verify_customer_payment')
#     def handle_customer_and_payment_verification(self, payload):
#         """ this event handler will add a payment method for a customer if the
#         provided values do not match any existing payment method assigned to the customer"""
#         customer_id = payload['customer_id']
#
#         customer = CustomerQueryModel.objects(id=customer_id).get()
#
#         if customer is None:
#             raise NotFound()
#
#         existing_payment = None
#
#         payment_methods = PaymentMethodQueryModel.objects(customer=customer_id)
#
#         for payment in payment_methods:
#             if payment.is_equal_to(payload['card_type_id', 'card_number', 'expiration']):
#                 existing_payment = payment
#                 break
#
#         if existing_payment is not None:
#             self.fire_event('payment_method', PaymentMethodSchema().dumps(existing_payment).data)
#
#         payment = self.add_payment_method(payload)
#
#         self.fire_event('cust_and_pay_method_verified', PaymentMethodSchema().dumps(payment).data)
