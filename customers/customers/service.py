import json
import logging

from nameko.events import event_handler, EventDispatcher
from nameko.rpc import rpc
from nameko_sqlalchemy import DatabaseSession

from .exceptions import *
from .models import *

logger = logging.getLogger(__name__)

REPLICATE_DB_EVENT = 'replicate_db_event'
COMMAND_SERVICE = 'command_customers'
QUERY_SERVICE = 'query_customers'
ORDERS_SERVICE = os.environ.get('ORDERS_COMMAND', 'command_orders')


class Command:
    name = COMMAND_SERVICE
    dispatch = EventDispatcher()
    db = DatabaseSession(DeclarativeBase)

    def _save_to_db(self, item):
        self.db.add(item)
        self.db.commit()

    def fire_replicate_db_event(self, data):
        self.dispatch(REPLICATE_DB_EVENT, data)

    @rpc
    def validate_account(self, id):
        return self.db.query(Account).get(id) is not None

    @rpc
    def register(self, data):
        """
        Creates a user account and customer profile, returns the new account id.

        Note that multiple customers can be added to the same account.
        :param data:
        :return:
        """
        if isinstance(data, str):
            data = json.loads(data)

        account = Account(user_name=data['user_name'], email=data['email'],
                          password_hash=data['password_hash'])

        self._save_to_db(account)

        data['account_id'] = account.id

        self.add_customer(data)

        return {'id': account.id}

    @rpc
    def update_password(self, id, password_hash):

        account = self.db.query(Account).get(id)

        account.password_hash = password_hash
        account.updated_at = datetime.datetime.utcnow()

        self._save_to_db(account)

    @rpc
    def add_customer(self, data):
        """
        Adds a new customer to the database
        :param data:
        :return:
        """

        if isinstance(data, str):
            data = json.loads(data)

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
        customer.account_id = data.get('account_id')

        customer.full_name = f'{customer.name} {customer.last_name}'

        self._save_to_db(customer)

        data['id'] = customer.id
        data['full_name'] = customer.full_name
        data['created_at'] = customer.created_at
        data['updated_at'] = customer.updated_at

        self.fire_replicate_db_event(data)

        return data

    @rpc
    def update_customer(self, id, data):
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

        customer.full_name = f'{customer.name} {customer.last_name}'

        self._save_to_db(customer)

        data['full_name'] = customer.full_name
        data['created_at'] = customer.created_at
        data['updated_at'] = customer.updated_at

        self.fire_replicate_db_event(data)

        return data


class Query:
    name = QUERY_SERVICE

    @event_handler(COMMAND_SERVICE, REPLICATE_DB_EVENT)
    def normalize_db(self, data):
        """ with the incoming payload:
        check to see if the record already exists in the query database
        if so, updated it with the new replicated values, otherwise add
        the record to the query database"""

        if isinstance(data, str):
            data = json.loads(data)

        try:
            customer = QueryCustomersModel.objects.get(
                id=data['id']
            )

            customer.update(
                name=data.get('name', customer.name),
                phone=data.get('phone', customer.phone),
                email=data.get('email', customer.email),
                full_name=data.get('full_name', customer.full_name),
                last_name=data.get('last_name', customer.last_name),
                state=data.get('state', customer.state),
                street_2=data.get('street_2', customer.street_2),
                street_1=data.get('street_1', customer.street_1),
                city=data.get('city', customer.city),
                country=data.get('country', customer.country),
                zip_code=data.get('zip_code', customer.zip_code),
                created_at=data.get('created_at', customer.created_at),
                updated_at=data.get('updated_at', customer.updated_at),
                account_id=data.get('account_id', customer.account_id)
            )
            customer.reload()
        except DoesNotExist:
            QueryCustomersModel(
                id=data['id'],
                full_name=data['full_name'],
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
                updated_at=data['updated_at'],
                account_id=data['account_id']
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
